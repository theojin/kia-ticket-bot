"""
ticket/navigator.py - 상품 페이지 이동 및 대기열 진입

티켓 상품 페이지로 이동하고 판매 시작 시 대기열에 진입합니다.

NOTE: 실제 선택자는 NOL 티켓 사이트를 DevTools로 확인 후 업데이트하세요.
"""

import asyncio

from patchright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from loguru import logger

from config import Config
from src.utils.timing import human_delay, wait_until

# 상품 페이지 URL 패턴
GOODS_URL_TEMPLATE = "https://ticket.interpark.com/goods/{goods_id}"

# 선택자 (DevTools로 확인 후 업데이트 필요)
SELECTOR_BUY_BUTTON = "button.buy-btn, a.purchase-btn, .btn-buy, button[data-action='buy']"
SELECTOR_QUEUE_WAIT = ".queue-wait, .waiting-area, #queue"
SELECTOR_QUEUE_COMPLETE = ".queue-complete, .seat-select-area"


async def navigate_to_goods(page: Page, config: Config) -> bool:
    """
    티켓 상품 페이지로 이동합니다.

    Returns:
        이동 성공 여부
    """
    url = GOODS_URL_TEMPLATE.format(goods_id=config.goods_id)
    logger.info(f"상품 페이지 이동: {url}")

    try:
        await page.goto(url, wait_until="networkidle", timeout=20000)
        await human_delay(0.5, 1.0)
        logger.info("상품 페이지 로드 완료")
        return True
    except Exception as e:
        logger.error(f"상품 페이지 이동 실패: {e}")
        return False


async def click_buy_button(page: Page) -> bool:
    """
    구매 버튼을 클릭해 대기열에 진입합니다.
    판매 시작 전에도 버튼이 보이는 경우 force=True로 클릭을 강제합니다.

    Returns:
        클릭 성공 여부
    """
    try:
        buy_btn = page.locator(SELECTOR_BUY_BUTTON)

        # 버튼이 화면에 보일 때까지 대기 (최대 5초)
        await buy_btn.wait_for(state="visible", timeout=5000)

        # 마우스를 버튼 위로 먼저 이동 (자연스러운 동작)
        box = await buy_btn.bounding_box()
        if box:
            import random
            await page.mouse.move(
                box["x"] + box["width"] * random.uniform(0.3, 0.7),
                box["y"] + box["height"] * random.uniform(0.3, 0.7),
                steps=random.randint(5, 10),
            )
            await human_delay(0.05, 0.15)

        # force=True: disabled 상태여도 클릭 강제 (오픈 직전 선점)
        await buy_btn.click(force=True)
        logger.info("구매 버튼 클릭 완료 - 대기열 진입")
        return True

    except PlaywrightTimeoutError:
        logger.error("구매 버튼을 찾을 수 없습니다. 선택자를 확인하세요.")
        return False
    except Exception as e:
        logger.error(f"구매 버튼 클릭 실패: {e}")
        return False


async def wait_for_queue(page: Page, timeout_sec: int = 600) -> bool:
    """
    대기열 통과를 기다립니다.

    Args:
        timeout_sec: 최대 대기 시간 (초). 기본 10분.

    Returns:
        대기열 통과 성공 여부
    """
    logger.info("대기열 대기 중...")

    try:
        # 대기열 완료(좌석 선택 화면 진입) 감지
        await page.wait_for_selector(
            SELECTOR_QUEUE_COMPLETE,
            timeout=timeout_sec * 1000
        )
        logger.info("대기열 통과! 좌석 선택 화면으로 진입")
        return True
    except PlaywrightTimeoutError:
        logger.error(f"대기열 타임아웃 ({timeout_sec}초)")
        return False
