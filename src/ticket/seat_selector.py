"""
ticket/seat_selector.py - 좌석 선택 자동화 (잠실야구장)

우선순위 구역 순서대로 좌석을 시도합니다.
  1순위: 112, 113구역 (중앙 테이블석) - 3석 연석
  2순위: 318, 319구역 (중앙 네이비석)
  3순위: 나머지 KIA 응원석 (3루 방향)

NOTE: 잠실야구장 좌석 맵의 실제 선택자/좌표는 DevTools로 확인 후
      docs/SEAT_MAP.md에 기록하고 아래 상수를 업데이트하세요.
"""

from __future__ import annotations

import random

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from loguru import logger

from config import Config
from src.utils.timing import human_delay

# 구역별 선택자 (DevTools로 확인 후 업데이트 필요)
# 좌석 맵이 Canvas 기반이면 좌표 방식 사용 (docs/SEAT_MAP.md 참고)
SECTION_SELECTOR_TEMPLATE = (
    "[data-section='{section}'], "
    ".section-{section}, "
    "[aria-label*='{section}'], "
    ".seat-area:has-text('{section}')"
)

# 수량 선택 버튼 (DevTools로 확인 필요)
SELECTOR_QTY_PLUS = ".quantity-plus, button.plus, [data-action='increase']"
SELECTOR_QTY_MINUS = ".quantity-minus, button.minus, [data-action='decrease']"
SELECTOR_QTY_VALUE = ".quantity-value, .seat-count, input.qty"

# 좌석 확정 버튼
SELECTOR_SEAT_CONFIRM = (
    "button.seat-confirm, .btn-reserve, "
    "button:has-text('선택 완료'), button:has-text('다음')"
)


async def select_seats(page: Page, config: Config) -> str | None:
    """
    우선순위 구역에서 지정된 매수만큼 좌석을 선택합니다.

    Returns:
        성공한 구역명 (예: "112") 또는 None (전 구역 실패)
    """
    for section in config.preferred_sections:
        logger.info(f"구역 시도: {section}")
        success = await _try_select_section(page, section, config.max_tickets)
        if success:
            logger.info(f"좌석 선택 성공: {section}구역 {config.max_tickets}석")
            return section
        logger.info(f"{section}구역 선택 실패 - 다음 구역으로")

    logger.error("모든 선호 구역 선택 실패")
    return None


async def _try_select_section(page: Page, section: str, quantity: int) -> bool:
    """
    특정 구역에서 좌석 선택을 시도합니다.

    Returns:
        성공 여부
    """
    selector = SECTION_SELECTOR_TEMPLATE.format(section=section)

    try:
        section_el = page.locator(selector).first
        count = await section_el.count()

        if count == 0:
            logger.debug(f"{section}구역 요소 없음 (좌석맵 선택자 확인 필요)")
            return False

        # 구역 클릭
        box = await section_el.bounding_box()
        if box:
            await page.mouse.move(
                box["x"] + box["width"] * random.uniform(0.3, 0.7),
                box["y"] + box["height"] * random.uniform(0.3, 0.7),
                steps=random.randint(3, 8),
            )
        await section_el.click()
        await human_delay(0.5, 1.0)

        # 수량 설정
        await _set_quantity(page, quantity)
        await human_delay(0.3, 0.7)

        # 좌석 확정 버튼 클릭
        confirm_btn = page.locator(SELECTOR_SEAT_CONFIRM).first
        if not await confirm_btn.is_visible():
            logger.debug(f"{section}구역 확정 버튼 없음")
            return False

        if not await confirm_btn.is_enabled():
            logger.debug(f"{section}구역 좌석 없음 (매진)")
            return False

        await confirm_btn.click()
        await human_delay(0.5, 1.0)

        # 좌석 선택 후 페이지 전환 확인
        await page.wait_for_load_state("networkidle", timeout=10000)
        return True

    except PlaywrightTimeoutError:
        logger.debug(f"{section}구역 타임아웃")
        return False
    except Exception as e:
        logger.warning(f"{section}구역 선택 중 오류: {e}")
        return False


async def _set_quantity(page: Page, quantity: int) -> None:
    """수량을 지정된 값으로 설정합니다."""
    try:
        # 현재 수량 확인
        qty_el = page.locator(SELECTOR_QTY_VALUE).first
        if not await qty_el.is_visible():
            return

        current_text = await qty_el.inner_text()
        current = int(current_text.strip()) if current_text.strip().isdigit() else 1

        # 수량 조정 (+ 또는 - 버튼 클릭)
        diff = quantity - current
        selector = SELECTOR_QTY_PLUS if diff > 0 else SELECTOR_QTY_MINUS
        btn = page.locator(selector).first

        for _ in range(abs(diff)):
            await btn.click()
            await human_delay(0.1, 0.3)

    except Exception as e:
        logger.debug(f"수량 설정 실패 (기본값 사용): {e}")
