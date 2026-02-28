"""tests/test_cookies.py - browser/cookies.py 유닛 테스트"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.browser.cookies import clear_cookies, load_cookies, save_cookies


@pytest.fixture
def cookie_file(tmp_path, monkeypatch) -> Path:
    """테스트마다 격리된 임시 쿠키 파일 경로."""
    temp_file = tmp_path / "session.json"
    monkeypatch.setattr("src.browser.cookies.COOKIES_FILE", temp_file)
    return temp_file


class TestSaveCookies:
    async def test_writes_cookies_to_file(self, cookie_file):
        cookies = [{"name": "SESSION", "value": "abc123", "domain": ".interpark.com"}]
        context = MagicMock()
        context.cookies = AsyncMock(return_value=cookies)

        await save_cookies(context)

        assert cookie_file.exists()
        saved = json.loads(cookie_file.read_text(encoding="utf-8"))
        assert saved == cookies

    async def test_saves_empty_cookie_list(self, cookie_file):
        context = MagicMock()
        context.cookies = AsyncMock(return_value=[])

        await save_cookies(context)

        assert cookie_file.exists()
        assert json.loads(cookie_file.read_text()) == []

    async def test_gracefully_handles_write_error(self, tmp_path, monkeypatch):
        """파일 저장 실패 시 예외 없이 넘어가야 함."""
        monkeypatch.setattr(
            "src.browser.cookies.COOKIES_FILE",
            tmp_path / "no_such_dir" / "session.json",
        )
        context = MagicMock()
        context.cookies = AsyncMock(return_value=[])

        await save_cookies(context)  # 예외 없이 완료


class TestLoadCookies:
    async def test_returns_false_when_file_absent(self, cookie_file):
        context = MagicMock()
        context.add_cookies = AsyncMock()

        result = await load_cookies(context)

        assert result is False
        context.add_cookies.assert_not_called()

    async def test_loads_cookies_and_returns_true(self, cookie_file):
        cookies = [{"name": "SESSION", "value": "xyz"}]
        cookie_file.write_text(json.dumps(cookies), encoding="utf-8")

        context = MagicMock()
        context.add_cookies = AsyncMock()

        result = await load_cookies(context)

        assert result is True
        context.add_cookies.assert_called_once_with(cookies)

    async def test_returns_false_on_invalid_json(self, cookie_file):
        cookie_file.write_text("이건 JSON이 아님", encoding="utf-8")
        context = MagicMock()
        context.add_cookies = AsyncMock()

        result = await load_cookies(context)

        assert result is False

    async def test_returns_false_when_add_cookies_raises(self, cookie_file):
        cookies = [{"name": "SESSION", "value": "xyz"}]
        cookie_file.write_text(json.dumps(cookies), encoding="utf-8")

        context = MagicMock()
        context.add_cookies = AsyncMock(side_effect=Exception("브라우저 오류"))

        result = await load_cookies(context)

        assert result is False


class TestClearCookies:
    def test_deletes_existing_cookie_file(self, cookie_file):
        cookie_file.write_text("[]", encoding="utf-8")
        assert cookie_file.exists()

        clear_cookies()

        assert not cookie_file.exists()

    def test_no_error_when_file_already_missing(self, cookie_file):
        assert not cookie_file.exists()
        clear_cookies()  # 예외 없이 완료
