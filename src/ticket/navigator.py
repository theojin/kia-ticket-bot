"""
ticket/navigator.py - 상품 페이지 이동 및 대기열 진입

티켓 상품 페이지로 이동하고 판매 시작 시 대기열에 진입합니다.
스포츠 모드: 팀 페이지 → 예매하기 클릭 → 팝업(대기열 → BookMain)
"""

from __future__ import annotations

import asyncio

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from loguru import logger

from config import Config
from src.utils.timing import human_delay

# 상품 페이지 URL 패턴
GOODS_URL_TEMPLATE = "https://tickets.interpark.com/goods/{goods_id}"

# 스포츠 팀 페이지 URL 패턴
SPORTS_TEAM_URL_TEMPLATE = (
    "https://ticket.interpark.com/Contents/Sports/GoodsInfo"
    "?SportsCode={sports_code}&TeamCode={team_code}"
)

# 선택자 (DevTools로 확인 후 업데이트 필요)
SELECTOR_BUY_BUTTON = "button.buy-btn, a.purchase-btn, .btn-buy, button[data-action='buy']"
SELECTOR_QUEUE_WAIT = ".queue-wait, .waiting-area, #queue"
SELECTOR_QUEUE_COMPLETE = ".queue-complete, .seat-select-area"


async def navigate_to_goods(page: Page, config: Config) -> Page | None:
    """
    티켓 상품 페이지로 이동합니다.
    스포츠 모드인 경우 팝업을 열고 대기열을 통과합니다.

    Returns:
        예매가 진행될 Page 객체 (스포츠=팝업, 일반=원래 page). 실패 시 None.
    """
    if config.is_sports:
        return await _navigate_to_sports_game(page, config)

    url = GOODS_URL_TEMPLATE.format(goods_id=config.goods_id)
    logger.info(f"상품 페이지 이동: {url}")

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await human_delay(0.5, 1.0)
        logger.info("상품 페이지 로드 완료")
        return page
    except Exception as e:
        logger.error(f"상품 페이지 이동 실패: {e}")
        return None


async def _navigate_to_sports_game(page: Page, config: Config) -> Page | None:
    """
    스포츠 팀 페이지 → 예매하기 클릭 → 팝업(대기열 통과) → BookMain 도착.

    Returns:
        예매 팝업 Page 객체 또는 None
    """
    team_url = SPORTS_TEAM_URL_TEMPLATE.format(
        sports_code=config.sports_code,
        team_code=config.team_code,
    )
    logger.info(f"스포츠 팀 페이지 이동: {team_url}")

    try:
        await page.goto(team_url, wait_until="domcontentloaded", timeout=20000)
        await human_delay(0.5, 1.0)
        logger.info("팀 페이지 로드 완료")
    except Exception as e:
        logger.error(f"팀 페이지 이동 실패: {e}")
        return None

    # 예매하기 버튼 클릭 + 팝업 감지
    try:
        book_btn = page.locator(f"a[onclick*='{config.goods_id}']").first
        btn_count = await book_btn.count()
        if btn_count == 0:
            # fallback: 텍스트로 검색
            book_btn = page.locator("a:has-text('예매하기')").first
        logger.info("예매하기 버튼 클릭...")

        async with page.expect_popup(timeout=15000) as popup_info:
            await book_btn.click()

        popup = await popup_info.value
        logger.info(f"팝업 열림: {popup.url[:80]}")
    except PlaywrightTimeoutError:
        logger.error("예매하기 팝업 감지 타임아웃")
        return None
    except Exception as e:
        logger.error(f"예매하기 클릭 실패: {e}")
        return None

    # 대기열 통과 대기 (waiting → poticket.interpark.com)
    logger.info("대기열 통과 대기 중...")
    for i in range(60):
        await asyncio.sleep(1)
        if "poticket.interpark.com" in popup.url:
            logger.info(f"대기열 통과! ({i+1}초)")
            await asyncio.sleep(3)  # iframe 로드 대기
            return popup
    logger.error("대기열 통과 타임아웃 (60초)")
    return None


async def click_buy_button(page: Page) -> bool:
    """
    구매 버튼을 클릭해 대기열에 진입합니다.

    Returns:
        클릭 성공 여부
    """
    try:
        buy_btn = page.locator(SELECTOR_BUY_BUTTON)
        await buy_btn.wait_for(state="visible", timeout=5000)

        box = await buy_btn.bounding_box()
        if box:
            import random
            await page.mouse.move(
                box["x"] + box["width"] * random.uniform(0.3, 0.7),
                box["y"] + box["height"] * random.uniform(0.3, 0.7),
                steps=random.randint(5, 10),
            )
            await human_delay(0.05, 0.15)

        await buy_btn.click(force=True)
        logger.info("구매 버튼 클릭 완료 - 대기열 진입")
        return True

    except PlaywrightTimeoutError:
        logger.error("구매 버튼을 찾을 수 없습니다.")
        return False
    except Exception as e:
        logger.error(f"구매 버튼 클릭 실패: {e}")
        return False


async def wait_for_queue(page: Page, timeout_sec: int = 600) -> bool:
    """
    대기열 통과를 기다립니다.

    Returns:
        대기열 통과 성공 여부
    """
    logger.info("대기열 대기 중...")

    try:
        await page.wait_for_selector(
            SELECTOR_QUEUE_COMPLETE,
            timeout=timeout_sec * 1000
        )
        logger.info("대기열 통과! 좌석 선택 화면으로 진입")
        return True
    except PlaywrightTimeoutError:
        logger.error(f"대기열 타임아웃 ({timeout_sec}초)")
        return False
