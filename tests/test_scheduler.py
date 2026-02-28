"""tests/test_scheduler.py - monitor/scheduler.py 유닛 테스트"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config import Config
from src.monitor.scheduler import check_clock_sync, run_at_sale_time

KST = timezone(timedelta(hours=9))


def _make_config(sale_offset_seconds: float) -> Config:
    """
    테스트용 Config 생성.

    pre_sale_activate_seconds=3600 으로 설정해 prepare_time 이 항상
    현재보다 과거가 되도록 하여, wait_until(prepare_time) 호출을 스킵합니다.
    이렇게 하면 테스트에서 wait_until 을 mock 할 때 레이스 부분만 제어할 수 있습니다.
    """
    sale_time = datetime.now(tz=KST) + timedelta(seconds=sale_offset_seconds)
    return Config(
        interpark_id="id",
        interpark_pw="pw",
        goods_id="12345",
        sale_start_time=sale_time,
        preferred_sections=["112"],
        max_tickets=3,
        card_number="0000-1111-2222-3333",
        card_expiry="1228",
        card_cvv="123",
        card_password_2digits="12",
        telegram_bot_token="token",
        telegram_chat_id="chat",
        polling_interval=0.5,
        pre_sale_activate_seconds=3600,  # prepare_time 을 항상 과거로
        headless=True,
        screenshot_on_error=False,
    )


class TestCheckClockSync:
    def test_returns_zero_when_ntp_unreachable(self):
        with patch("ntplib.NTPClient") as mock_ntp:
            mock_ntp.return_value.request.side_effect = Exception("NTP 불가")
            offset = check_clock_sync()
        assert offset == 0.0

    def test_returns_offset_on_success(self):
        mock_response = MagicMock()
        mock_response.offset = 0.123
        with patch("ntplib.NTPClient") as mock_ntp:
            mock_ntp.return_value.request.return_value = mock_response
            offset = check_clock_sync()
        assert offset == pytest.approx(0.123)

    def test_does_not_raise_on_any_exception(self):
        with patch("ntplib.NTPClient", side_effect=RuntimeError("예상치 못한 오류")):
            offset = check_clock_sync()
        assert offset == 0.0


class TestRunAtSaleTime:
    async def test_past_sale_time_calls_buy_immediately(self):
        """이미 오픈 시각이 지난 경우 즉시 구매를 시도해야 함."""
        config = _make_config(-10)
        on_prepare = AsyncMock()
        on_buy = AsyncMock(return_value=True)

        result = await run_at_sale_time(config, on_prepare, on_buy)

        assert result is True
        on_buy.assert_called_once()
        on_prepare.assert_not_called()

    async def test_returns_false_when_buy_fails(self):
        """on_buy 가 False 를 반환하면 결과도 False 여야 함."""
        config = _make_config(-5)
        on_prepare = AsyncMock()
        on_buy = AsyncMock(return_value=False)

        result = await run_at_sale_time(config, on_prepare, on_buy)

        assert result is False

    async def test_poll_trigger_fires_buy_before_time(self):
        """API 폴링이 시각보다 먼저 완료되면 구매가 즉시 실행되어야 함."""
        config = _make_config(100)  # 100초 후 오픈, prepare_time = -3500초(과거)
        on_prepare = AsyncMock()
        on_buy = AsyncMock(return_value=True)

        async def instant_poll(_config):
            return True  # 즉시 오픈 감지

        async def slow_wait(target_time, check_interval=0.01):
            await asyncio.sleep(1000)  # 실제로는 취소됨

        with patch("src.monitor.scheduler.poll_until_open", side_effect=instant_poll), \
             patch("src.monitor.scheduler.wait_until", side_effect=slow_wait):
            result = await run_at_sale_time(config, on_prepare, on_buy)

        assert result is True
        on_prepare.assert_called_once()
        on_buy.assert_called_once()

    async def test_time_trigger_fires_buy_before_poll(self):
        """시각 기반 트리거가 폴링보다 먼저 완료되면 구매가 실행되어야 함."""
        config = _make_config(100)
        on_prepare = AsyncMock()
        on_buy = AsyncMock(return_value=True)

        async def instant_wait(target_time, check_interval=0.01):
            return  # 즉시 반환

        async def slow_poll(_config):
            await asyncio.sleep(1000)  # 실제로는 취소됨

        with patch("src.monitor.scheduler.poll_until_open", side_effect=slow_poll), \
             patch("src.monitor.scheduler.wait_until", side_effect=instant_wait):
            result = await run_at_sale_time(config, on_prepare, on_buy)

        assert result is True
        on_prepare.assert_called_once()
        on_buy.assert_called_once()

    async def test_pending_tasks_cancelled_after_trigger(self):
        """레이스에서 패배한 task 는 취소되어야 함."""
        config = _make_config(100)
        on_prepare = AsyncMock()
        on_buy = AsyncMock(return_value=True)
        cancelled_tasks: list = []

        async def instant_poll(_config):
            return True

        async def slow_wait(target_time, check_interval=0.01):
            try:
                await asyncio.sleep(1000)
            except asyncio.CancelledError:
                cancelled_tasks.append("wait_until")
                raise

        with patch("src.monitor.scheduler.poll_until_open", side_effect=instant_poll), \
             patch("src.monitor.scheduler.wait_until", side_effect=slow_wait):
            await run_at_sale_time(config, on_prepare, on_buy)

        assert "wait_until" in cancelled_tasks
