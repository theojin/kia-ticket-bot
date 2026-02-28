"""
browser/cookies.py - 세션 쿠키 저장 및 로드

로그인 쿠키를 로컬에 저장해 재실행 시 재로그인을 방지합니다.
cookies/ 폴더는 .gitignore에 포함되어 절대 커밋되지 않습니다.
"""

import json
from pathlib import Path

from loguru import logger

COOKIES_DIR = Path("cookies")
COOKIES_DIR.mkdir(exist_ok=True)
COOKIES_FILE = COOKIES_DIR / "session.json"


async def save_cookies(context) -> None:
    """현재 브라우저 컨텍스트의 쿠키를 파일에 저장합니다."""
    try:
        cookies = await context.cookies()
        with open(COOKIES_FILE, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        logger.info(f"쿠키 저장 완료 ({len(cookies)}개)")
    except Exception as e:
        logger.warning(f"쿠키 저장 실패: {e}")


async def load_cookies(context) -> bool:
    """
    저장된 쿠키를 브라우저 컨텍스트에 로드합니다.

    Returns:
        쿠키 로드 성공 여부
    """
    if not COOKIES_FILE.exists():
        logger.info("저장된 쿠키 없음 (첫 실행 또는 초기화됨)")
        return False

    try:
        with open(COOKIES_FILE, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        await context.add_cookies(cookies)
        logger.info(f"쿠키 로드 완료 ({len(cookies)}개)")
        return True
    except Exception as e:
        logger.warning(f"쿠키 로드 실패 (새로 로그인 필요): {e}")
        return False


def clear_cookies() -> None:
    """저장된 쿠키 파일을 삭제합니다 (강제 재로그인 시 사용)."""
    if COOKIES_FILE.exists():
        COOKIES_FILE.unlink()
        logger.info("쿠키 파일 삭제 완료")
