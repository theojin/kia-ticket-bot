"""tests/test_screenshot.py - utils/screenshot.py 유닛 테스트"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.utils.screenshot import _is_payment_page, take_screenshot


class TestIsPaymentPage:
    @pytest.mark.parametrize("url,expected", [
        ("https://ticket.interpark.com/payment/confirm", True),
        ("https://example.com/pay/card", True),
        ("https://example.com/checkout/summary", True),
        ("https://example.com/PAYMENT/upper", True),   # 대소문자 무관
        ("https://ticket.interpark.com/goods/12345678", False),
        ("https://ticket.interpark.com/seat/select", False),
        ("https://ticket.interpark.com/queue/wait", False),
        ("https://ticket.interpark.com/order/complete", False),
    ])
    def test_identifies_payment_urls_correctly(self, url, expected):
        assert _is_payment_page(url) == expected


class TestTakeScreenshot:
    async def test_skips_screenshot_on_payment_page(self):
        page = MagicMock()
        page.url = "https://example.com/payment/confirm"
        page.screenshot = AsyncMock()

        result = await take_screenshot(page, "test")

        assert result is None
        page.screenshot.assert_not_called()

    async def test_saves_screenshot_on_safe_page(self, tmp_path):
        page = MagicMock()
        page.url = "https://ticket.interpark.com/seat/select"
        page.screenshot = AsyncMock()

        with patch("src.utils.screenshot.SCREENSHOTS_DIR", tmp_path):
            result = await take_screenshot(page, "seat_fail")

        assert result is not None
        assert "seat_fail" in result
        assert result.endswith(".png")
        page.screenshot.assert_called_once()

    async def test_screenshot_path_contains_label_and_timestamp(self, tmp_path):
        page = MagicMock()
        page.url = "https://ticket.interpark.com/goods/123"
        page.screenshot = AsyncMock()

        with patch("src.utils.screenshot.SCREENSHOTS_DIR", tmp_path):
            result = await take_screenshot(page, "crash")

        assert "crash" in result

    async def test_returns_none_when_screenshot_raises(self):
        page = MagicMock()
        page.url = "https://ticket.interpark.com/seat/select"
        page.screenshot = AsyncMock(side_effect=Exception("스크린샷 실패"))

        result = await take_screenshot(page, "test")

        assert result is None
