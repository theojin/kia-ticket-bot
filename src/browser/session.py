"""
browser/session.py - Patchright 브라우저 세션 생성

봇 탐지를 피하기 위한 설정을 적용한 브라우저 컨텍스트를 생성합니다.
Patchright는 Playwright의 CDP 레벨 봇 탐지 신호를 패치한 버전입니다.
"""

from __future__ import annotations

from patchright.async_api import async_playwright, Browser, BrowserContext, Page
from loguru import logger

from config import Config
from src.browser.cookies import load_cookies


async def create_session(config: Config) -> tuple[Browser, BrowserContext, Page]:
    """
    봇 탐지 우회 설정이 적용된 브라우저 세션을 생성합니다.

    Returns:
        (browser, context, page) 튜플
    """
    playwright = await async_playwright().start()

    browser = await playwright.chromium.launch(
        headless=config.headless,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-infobars",
            "--start-maximized",
        ],
    )

    context = await browser.new_context(
        # 한국 사용자 환경에 맞는 지문 설정
        viewport={"width": 1920, "height": 1080},
        locale="ko-KR",
        timezone_id="Asia/Seoul",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        extra_http_headers={
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,*/*;q=0.8"
            ),
        },
        permissions=["notifications"],
    )

    # 저장된 쿠키가 있으면 로드 (재로그인 방지)
    await load_cookies(context)

    page = await context.new_page()
    logger.info("브라우저 세션 생성 완료 (Patchright)")
    return browser, context, page


async def close_session(browser: Browser) -> None:
    """브라우저 세션을 종료합니다."""
    await browser.close()
    logger.info("브라우저 세션 종료")
