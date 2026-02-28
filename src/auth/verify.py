"""
auth/verify.py - 로그인 세션 유효성 확인

봇 실행 전 저장된 쿠키로 세션이 유효한지 확인합니다.
만료된 경우 재로그인을 수행합니다.
"""

from patchright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from loguru import logger

from config import Config
from src.auth.login import login, SELECTOR_LOGGED_IN

# 로그인 여부를 확인할 페이지 (마이페이지 등)
VERIFY_URL = "https://ticket.interpark.com"


async def ensure_logged_in(page: Page, config: Config) -> bool:
    """
    세션이 유효한지 확인하고, 만료된 경우 재로그인합니다.

    Returns:
        최종 로그인 성공 여부
    """
    logger.info("세션 유효성 확인 중...")

    try:
        await page.goto(VERIFY_URL, wait_until="networkidle", timeout=15000)
    except Exception as e:
        logger.warning(f"세션 확인 페이지 접속 실패: {e}")
        return await login(page, config)

    # 로그인 상태 확인
    try:
        await page.wait_for_selector(SELECTOR_LOGGED_IN, timeout=5000)
        logger.info("세션 유효 - 재로그인 불필요")
        return True
    except PlaywrightTimeoutError:
        logger.info("세션 만료 - 재로그인 시도")
        return await login(page, config)
