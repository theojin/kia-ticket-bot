"""
browser/session.py - 브라우저 세션 생성

실제 설치된 Chrome을 CDP(Chrome DevTools Protocol)로 제어합니다.
이 방식은 Patchright의 프레임 관리를 우회하며,
실제 Chrome 프로필을 사용하므로 봇 탐지에 가장 안전합니다.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from loguru import logger

from config import Config

# Chrome 프로필 저장 경로
PROFILE_DIR = Path.home() / ".kia-ticket-bot" / "chrome-profile"

# CDP 포트
CDP_PORT = 9222

# Chrome 실행 파일 경로 후보
CHROME_PATHS = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "Application" / "chrome.exe",
]


def _find_chrome() -> str:
    """설치된 Chrome 경로를 찾습니다."""
    for p in CHROME_PATHS:
        if p.exists():
            return str(p)
    raise FileNotFoundError(
        "Chrome이 설치되지 않았습니다. "
        "https://www.google.com/chrome 에서 설치해주세요."
    )


def _launch_chrome(headless: bool) -> subprocess.Popen:
    """원격 디버깅이 활성화된 Chrome을 실행합니다."""
    chrome_path = _find_chrome()
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    args = [
        chrome_path,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        "--start-maximized",
        "--disable-popup-blocking",
    ]
    if headless:
        args.append("--headless=new")

    logger.info("Chrome 실행 중...")
    process = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Chrome이 CDP 포트를 열 때까지 대기
    time.sleep(2)
    return process


async def create_session(config: Config) -> tuple[Browser, BrowserContext, Page]:
    """
    실제 Chrome에 CDP로 연결한 브라우저 세션을 생성합니다.

    Returns:
        (browser, context, page) 튜플
    """
    _launch_chrome(config.headless)

    playwright = await async_playwright().start()

    browser = await playwright.chromium.connect_over_cdp(
        f"http://localhost:{CDP_PORT}"
    )

    # 기존 컨텍스트와 페이지 사용
    context = browser.contexts[0] if browser.contexts else await browser.new_context()
    page = context.pages[0] if context.pages else await context.new_page()

    logger.info("브라우저 세션 생성 완료 (Chrome CDP)")
    return browser, context, page


async def close_session(browser: Browser) -> None:
    """브라우저 세션을 종료합니다."""
    try:
        await browser.close()
    except Exception:
        pass
    logger.info("브라우저 세션 종료")
