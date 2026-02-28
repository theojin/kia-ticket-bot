"""
utils/screenshot.py - 오류 발생 시 브라우저 스크린샷 저장

결제 화면은 카드 정보 노출 위험이 있으므로 촬영하지 않습니다.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from loguru import logger

SCREENSHOTS_DIR = Path("screenshots")
SCREENSHOTS_DIR.mkdir(exist_ok=True)

# 결제 관련 URL 패턴 - 이 페이지에서는 스크린샷 촬영 금지
PAYMENT_URL_PATTERNS = [
    "payment",
    "pay",
    "checkout",
    "card",
    "결제",
]


def _is_payment_page(url: str) -> bool:
    """결제 페이지 여부 확인 (스크린샷 금지 대상)."""
    url_lower = url.lower()
    return any(pattern in url_lower for pattern in PAYMENT_URL_PATTERNS)


async def take_screenshot(page, label: str = "error") -> str | None:
    """
    오류 발생 시 스크린샷 저장.
    결제 페이지에서는 카드 정보 보호를 위해 촬영하지 않습니다.

    Returns:
        저장된 파일 경로 또는 None (촬영 안 함)
    """
    try:
        current_url = page.url
        if _is_payment_page(current_url):
            logger.warning("결제 페이지 스크린샷은 보안상 촬영하지 않습니다.")
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = SCREENSHOTS_DIR / f"{label}_{timestamp}.png"
        await page.screenshot(path=str(filename))
        logger.info(f"스크린샷 저장: {filename}")
        return str(filename)

    except Exception as e:
        logger.error(f"스크린샷 저장 실패: {e}")
        return None
