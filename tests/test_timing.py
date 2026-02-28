"""tests/test_timing.py - utils/timing.py 유닛 테스트"""

import time
from datetime import datetime, timedelta, timezone

import pytest

from src.utils.timing import human_delay, random_typing_speed, seconds_until, wait_until


class TestRandomTypingSpeed:
    def test_returns_int(self):
        assert isinstance(random_typing_speed(), int)

    def test_value_within_range(self):
        for _ in range(200):
            speed = random_typing_speed()
            assert 50 <= speed <= 150, f"범위 초과: {speed}"


class TestSecondsUntil:
    def test_future_time_returns_positive(self):
        future = datetime.now(tz=timezone.utc) + timedelta(seconds=10)
        assert seconds_until(future) > 0

    def test_past_time_returns_negative(self):
        past = datetime.now(tz=timezone.utc) - timedelta(seconds=10)
        assert seconds_until(past) < 0

    def test_approximate_value(self):
        future = datetime.now(tz=timezone.utc) + timedelta(seconds=5)
        remaining = seconds_until(future)
        assert 4.9 < remaining <= 5.0

    def test_returns_float(self):
        target = datetime.now(tz=timezone.utc) + timedelta(seconds=3)
        assert isinstance(seconds_until(target), float)


class TestHumanDelay:
    async def test_completes_within_range(self):
        start = time.monotonic()
        await human_delay(0.05, 0.1)
        elapsed = time.monotonic() - start
        assert 0.04 <= elapsed < 0.3

    async def test_min_equals_max_sleeps_approximately(self):
        start = time.monotonic()
        await human_delay(0.1, 0.1)
        elapsed = time.monotonic() - start
        assert elapsed >= 0.08


class TestWaitUntil:
    async def test_past_time_returns_immediately(self):
        past = datetime.now(tz=timezone.utc) - timedelta(seconds=1)
        start = time.monotonic()
        await wait_until(past)
        elapsed = time.monotonic() - start
        assert elapsed < 0.1

    async def test_near_future_waits_correctly(self):
        future = datetime.now(tz=timezone.utc) + timedelta(milliseconds=150)
        start = time.monotonic()
        await wait_until(future)
        elapsed = time.monotonic() - start
        # 150ms 이상 대기, 그러나 너무 오래 걸리지 않아야 함
        assert elapsed >= 0.1
        assert elapsed < 0.5

    async def test_timezone_aware_datetime_required(self):
        """wait_until은 timezone-aware datetime을 사용해야 함."""
        # timezone-aware datetime 정상 동작 확인
        past = datetime.now(tz=timezone.utc) - timedelta(seconds=1)
        start = time.monotonic()
        await wait_until(past)
        elapsed = time.monotonic() - start
        assert elapsed < 0.2
