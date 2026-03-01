"""
ticket/payment.py - 결제 자동화

카드 직접 입력 방식으로 결제를 자동 완료합니다.
결제 화면에서는 보안상 스크린샷을 촬영하지 않습니다.

7분 타이머가 만료되기 전에 결제를 완료해야 합니다.
ISP/안심클릭 방식이 강제될 경우 Telegram + 소리 알림으로 수동 전환합니다.

NOTE: 결제창의 실제 선택자/iframe 구조는 DevTools로 확인 후 업데이트하세요.
"""

from __future__ import annotations

import asyncio

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from loguru import logger

from config import Config
from src.utils.timing import human_delay, random_typing_speed
from src.notify.telegram import Notifier
from src.notify.sound import play_alert

# 결제 관련 선택자 (DevTools로 확인 후 업데이트 필요)
SELECTOR_PROCEED_TO_PAYMENT = (
    "button.payment-btn, .btn-payment, "
    "button:has-text('결제하기'), button:has-text('결제 진행')"
)
SELECTOR_CARD_OPTION = (
    "#credit-card-option, [data-payment='card'], "
    "label:has-text('신용카드'), label:has-text('카드')"
)
SELECTOR_ORDER_COMPLETE = (
    ".order-complete, .success-message, "
    ".booking-complete, [class*='complete']"
)
SELECTOR_ORDER_NUMBER = (
    ".order-number, .booking-number, "
    "[class*='order-no'], [class*='reserv-no']"
)

# ISP/안심클릭 감지용 선택자
SELECTOR_ISP = "iframe[src*='isp'], iframe[src*='ansimclick'], .isp-payment"

# 결제 완료까지 허용 시간 (7분 - 여유 30초)
PAYMENT_TIMEOUT_SEC = 390

# 카드 정보 iframe 선택자 (대부분 iframe 내부에 있음)
CARD_IFRAME_SELECTOR = "iframe[id*='card'], iframe[src*='card'], iframe[title*='카드']"


async def complete_payment(page: Page, config: Config, notifier: Notifier) -> str | None:
    """
    결제를 완료합니다.

    Returns:
        주문번호 (성공 시) 또는 None (실패 시)
    """
    logger.info("결제 페이지로 이동 중...")

    try:
        # 결제하기 버튼 클릭 (팝업 또는 새 탭 처리)
        async with page.context.expect_page() as popup_info:
            proceed_btn = page.locator(SELECTOR_PROCEED_TO_PAYMENT).first
            await proceed_btn.click()

        payment_page = await popup_info.value
        await payment_page.wait_for_load_state("networkidle", timeout=15000)

    except Exception:
        # 팝업이 아닌 같은 페이지에서 결제창이 열리는 경우
        payment_page = page
        try:
            await page.locator(SELECTOR_PROCEED_TO_PAYMENT).first.click()
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception as e:
            logger.error(f"결제 페이지 이동 실패: {e}")
            return None

    # ISP/안심클릭 방식 감지
    if await _is_isp_required(payment_page):
        logger.warning("ISP/안심클릭 방식이 감지되었습니다. 수동 결제가 필요합니다.")
        await notifier.notify_manual_payment_needed()
        await play_alert("payment_manual")
        # 수동 결제 완료 대기
        return await _wait_for_manual_payment(payment_page)

    # 카드 직접 입력 결제
    return await _pay_with_card(payment_page, config, notifier)


async def _is_isp_required(page: Page) -> bool:
    """ISP/안심클릭 방식 결제창인지 확인합니다."""
    try:
        await page.wait_for_selector(SELECTOR_ISP, timeout=2000)
        return True
    except PlaywrightTimeoutError:
        return False


async def _pay_with_card(page: Page, config: Config, notifier: Notifier) -> str | None:
    """카드 직접 입력으로 결제합니다."""
    logger.info("카드 직접 입력 결제 시작")

    try:
        # 카드 결제 옵션 선택
        await page.locator(SELECTOR_CARD_OPTION).first.click()
        await human_delay(0.5, 1.0)

        # 카드 정보 입력 (iframe 내부인 경우 처리)
        await _fill_card_info(page, config)
        await human_delay(0.5, 1.0)

        # 최종 결제 확인 버튼
        final_btn = page.locator(
            "button.final-confirm, button:has-text('결제'), "
            "button:has-text('확인'), button[type='submit']"
        ).first
        await final_btn.click()

        # 결제 완료 대기
        await page.wait_for_selector(
            SELECTOR_ORDER_COMPLETE,
            timeout=PAYMENT_TIMEOUT_SEC * 1000
        )

        # 주문번호 추출
        order_number = await _extract_order_number(page)
        logger.info(f"결제 완료! 주문번호: {order_number}")
        return order_number

    except PlaywrightTimeoutError:
        logger.error("결제 타임아웃")
        return None
    except Exception as e:
        logger.error(f"결제 중 오류: {e}")
        return None


async def _fill_card_info(page: Page, config: Config) -> None:
    """카드 정보를 입력합니다. iframe이 있으면 iframe 내부에서 처리합니다."""
    # 일반 입력 필드 시도
    try:
        card_frame = page.frame_locator(CARD_IFRAME_SELECTOR)

        # 카드번호 (4자리씩 나뉜 경우 대비)
        card_digits = config.card_number.replace("-", "").replace(" ", "")
        fields = [
            card_frame.locator("input[name*='cardNum1'], input[id*='cardNum1']"),
            card_frame.locator("input[name*='cardNum2'], input[id*='cardNum2']"),
            card_frame.locator("input[name*='cardNum3'], input[id*='cardNum3']"),
            card_frame.locator("input[name*='cardNum4'], input[id*='cardNum4']"),
        ]

        chunks = [card_digits[i:i+4] for i in range(0, 16, 4)]
        for field, chunk in zip(fields, chunks):
            try:
                await field.type(chunk, delay=random_typing_speed())
                await human_delay(0.1, 0.3)
            except Exception:
                pass

        # 유효기간
        expiry = card_frame.locator("input[name*='expiry'], input[id*='expiry']")
        await expiry.type(config.card_expiry, delay=random_typing_speed())
        await human_delay(0.2, 0.4)

        # CVV
        cvv = card_frame.locator("input[name*='cvv'], input[name*='cvc'], input[id*='cvv']")
        await cvv.type(config.card_cvv, delay=random_typing_speed())
        await human_delay(0.2, 0.4)

        # 비밀번호 앞 2자리
        pwd = card_frame.locator("input[name*='password'], input[id*='pwd']")
        await pwd.type(config.card_password_2digits, delay=random_typing_speed())

    except Exception as e:
        logger.warning(f"iframe 내 카드 입력 실패, 일반 필드 시도: {e}")
        # iframe 없이 직접 입력 시도 (간략화)
        await page.fill("input[name*='cardNum']", config.card_number[:4])


async def _extract_order_number(page: Page) -> str:
    """결제 완료 페이지에서 주문번호를 추출합니다."""
    try:
        el = page.locator(SELECTOR_ORDER_NUMBER).first
        text = await el.inner_text()
        return text.strip()
    except Exception:
        return "주문번호 확인 필요"


async def _wait_for_manual_payment(page: Page) -> str | None:
    """수동 결제 완료를 대기합니다."""
    logger.info(f"수동 결제 대기 중... ({PAYMENT_TIMEOUT_SEC}초)")
    try:
        await page.wait_for_selector(
            SELECTOR_ORDER_COMPLETE,
            timeout=PAYMENT_TIMEOUT_SEC * 1000
        )
        return await _extract_order_number(page)
    except PlaywrightTimeoutError:
        logger.error("수동 결제 타임아웃")
        return None
