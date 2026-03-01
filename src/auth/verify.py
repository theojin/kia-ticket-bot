"""
auth/verify.py - 로그인 세션 유효성 확인

nol.interpark.com 페이지에서 실제 로그인 상태를 확인합니다.
페이지에 '로그인' 버튼이 보이면 클릭하여 자동 로그인을 시도합니다.
"""

from playwright.async_api import Page
from loguru import logger

from config import Config
from src.auth.login import login, _try_auto_login


async def ensure_logged_in(page: Page, config: Config) -> bool:
    """
    nol.interpark.com에 접속하여 실제 로그인 상태를 확인합니다.
    '로그인' 버튼이 보이면 클릭하여 자동 로그인을 시도하고,
    실패하면 수동 로그인을 안내합니다.

    Returns:
        최종 로그인 성공 여부
    """
    logger.info("로그인 상태 확인 중...")

    # nol.interpark.com 접속
    try:
        await page.goto(
            "https://nol.interpark.com",
            wait_until="domcontentloaded",
            timeout=30000,
        )
    except Exception as e:
        logger.error(f"사이트 접속 실패: {e}")
        return False

    # 페이지에서 '로그인' 버튼이 보이는지 확인 (= 미로그인 상태)
    login_btn = page.locator("a:has-text('로그인'), button:has-text('로그인')").first
    if await login_btn.count() > 0:
        logger.info("로그인 버튼 발견 - 자동 로그인 시도...")
        if await _try_auto_login(page):
            logger.info("자동 로그인 성공!")
            return True

        # 자동 로그인 실패 → 수동 로그인 안내
        logger.info("자동 로그인 실패 - 수동 로그인 필요")
        return await login(page, config)

    logger.info("이미 로그인된 상태입니다.")
    return True
