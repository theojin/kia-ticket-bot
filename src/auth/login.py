"""
auth/login.py - NOL 티켓 로그인

Chrome CDP로 브라우저를 제어하며, 사용자가 직접 로그인하도록 안내합니다.
(카카오, 야놀자, 인터파크 등 원하는 방식으로 로그인 가능)
로그인 완료를 쿠키로 자동 감지합니다.
"""

import asyncio

from playwright.async_api import Page, BrowserContext, TimeoutError as PlaywrightTimeoutError
from loguru import logger

from config import Config

# 로그인 성공 시 존재하는 쿠키 도메인
_LOGIN_COOKIE_DOMAINS = [".accounts.kakao.com", ".interpark.com", ".nol.interpark.com"]

# 로그인 감지 임계값 (이 수 이상이면 로그인 상태로 판단)
_LOGIN_COOKIE_THRESHOLD = 5

# 로그인 대기 시간 (초)
MANUAL_LOGIN_TIMEOUT = 60

# 로그인 상태 선택자 (verify.py에서 import해서 사용)
SELECTOR_LOGGED_IN = "NOT_USED"


async def login(page: Page, config: Config) -> bool:
    """
    사용자에게 수동 로그인을 안내하고 완료를 대기합니다.
    ensure_logged_in에서 자동 로그인 실패 시 호출됩니다.

    Returns:
        로그인 성공 여부
    """
    context = page.context

    logger.warning("=" * 50)
    logger.warning("브라우저에서 직접 로그인해주세요!")
    logger.warning("  1. '로그인' 버튼 클릭")
    logger.warning("  2. '카카오로 시작하기' 클릭")
    logger.warning("  3. 카카오 계정으로 로그인")
    logger.warning(f"  {MANUAL_LOGIN_TIMEOUT}초 동안 대기합니다.")
    logger.warning("=" * 50)

    # 대기 (사용자가 로그인하는 동안 방해하지 않음)
    await asyncio.sleep(MANUAL_LOGIN_TIMEOUT)

    # 로그인 확인
    if await _check_login_cookies(context):
        logger.info("로그인 성공!")
        return True

    logger.error("로그인이 감지되지 않았습니다.")
    return False


async def _try_auto_login(page: Page) -> bool:
    """
    로그인 버튼을 클릭해 자동 로그인을 시도합니다.
    Chrome 프로필에 세션이 남아있으면 버튼 클릭만으로 로그인됩니다.

    Returns:
        자동 로그인 성공 여부
    """
    context = page.context

    try:
        # 로그인 버튼 찾기 (nol.interpark.com 헤더의 로그인 링크)
        login_btn = page.locator(
            "a:has-text('로그인'), button:has-text('로그인')"
        ).first
        if await login_btn.count() == 0:
            logger.debug("로그인 버튼을 찾을 수 없음")
            return False

        logger.info("로그인 버튼 클릭 시도...")
        await login_btn.click()
        await asyncio.sleep(5)

        # 클릭 후 로그인 쿠키 확인 (자동 로그인 성공 시)
        if await _check_login_cookies(context):
            return True

        # 페이지 이동이 발생했을 수 있으므로 추가 대기
        for _ in range(5):
            await asyncio.sleep(2)
            if await _check_login_cookies(context):
                return True

    except Exception as e:
        logger.debug(f"자동 로그인 시도 실패: {e}")

    return False


async def _check_login_cookies(context: BrowserContext) -> bool:
    """쿠키를 확인해 로그인 상태를 판단합니다."""
    try:
        cookies = await context.cookies()
        count = sum(
            1 for c in cookies
            if any(d in c.get("domain", "") for d in _LOGIN_COOKIE_DOMAINS)
        )
        return count >= _LOGIN_COOKIE_THRESHOLD
    except Exception:
        return False
