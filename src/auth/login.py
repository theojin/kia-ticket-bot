"""
auth/login.py - NOL 티켓 로그인 자동화

인간적인 타이핑 딜레이를 적용해 봇 탐지를 최소화합니다.
로그인 성공 시 쿠키를 저장해 다음 실행 시 재로그인을 방지합니다.

NOTE: 실제 선택자(selector)는 NOL 티켓 사이트를 브라우저 DevTools로 직접
      확인한 후 아래 상수를 업데이트해야 합니다.
"""

from patchright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from loguru import logger

from config import Config
from src.browser.cookies import save_cookies
from src.utils.timing import human_delay, random_typing_speed

# NOL 티켓 로그인 URL (리브랜딩 후 변경될 수 있음 - 직접 확인 필요)
LOGIN_URL = "https://accounts.interpark.com/login"

# 로그인 폼 선택자 (DevTools로 확인 후 업데이트 필요)
SELECTOR_ID_INPUT = "#userId"
SELECTOR_PW_INPUT = "#userPw"
SELECTOR_LOGIN_BTN = "button[type='submit']"
SELECTOR_LOGGED_IN = ".user-menu, .my-page-btn, .btn-mypage"


async def login(page: Page, config: Config) -> bool:
    """
    NOL 티켓에 로그인합니다.

    Returns:
        로그인 성공 여부
    """
    logger.info(f"로그인 시도: {LOGIN_URL}")

    try:
        await page.goto(LOGIN_URL, wait_until="networkidle", timeout=15000)
    except Exception as e:
        logger.error(f"로그인 페이지 접속 실패: {e}")
        return False

    await human_delay(1.0, 2.0)

    try:
        # ID 입력
        await page.locator(SELECTOR_ID_INPUT).click()
        await human_delay(0.3, 0.6)
        await page.locator(SELECTOR_ID_INPUT).type(
            config.interpark_id, delay=random_typing_speed()
        )

        await human_delay(0.4, 0.8)

        # 비밀번호 입력
        await page.locator(SELECTOR_PW_INPUT).click()
        await human_delay(0.2, 0.5)
        await page.locator(SELECTOR_PW_INPUT).type(
            config.interpark_pw, delay=random_typing_speed()
        )

        await human_delay(0.5, 1.0)

        # 로그인 버튼 클릭
        await page.locator(SELECTOR_LOGIN_BTN).click()

        # 로그인 완료 대기 (로그인 페이지에서 벗어날 때까지)
        await page.wait_for_url(
            lambda url: "login" not in url.lower(),
            timeout=10000
        )

    except PlaywrightTimeoutError:
        logger.error("로그인 타임아웃 - 선택자가 변경되었을 수 있습니다.")
        logger.error(f"현재 URL: {page.url}")
        return False
    except Exception as e:
        logger.error(f"로그인 중 오류: {e}")
        return False

    # 로그인 성공 확인
    success = await _verify_logged_in(page)
    if success:
        logger.info("로그인 성공")
        await save_cookies(page.context)
    else:
        logger.error("로그인 실패 - 아이디/비밀번호를 확인하세요.")

    return success


async def _verify_logged_in(page: Page) -> bool:
    """로그인된 상태인지 확인합니다."""
    try:
        await page.wait_for_selector(SELECTOR_LOGGED_IN, timeout=5000)
        return True
    except PlaywrightTimeoutError:
        return False
