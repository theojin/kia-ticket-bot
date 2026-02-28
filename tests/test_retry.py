"""tests/test_retry.py - utils/retry.py 유닛 테스트"""

from unittest.mock import AsyncMock, patch

import pytest

from src.utils.retry import async_retry


class TestAsyncRetry:
    async def test_success_on_first_attempt(self):
        mock = AsyncMock(return_value="result")
        decorated = async_retry(max_attempts=3)(mock)
        result = await decorated()
        assert result == "result"
        assert mock.call_count == 1

    async def test_retries_and_eventually_succeeds(self):
        call_count = 0

        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("일시적 오류")
            return "success"

        decorated = async_retry(max_attempts=3, delay=0.01)(flaky)
        result = await decorated()
        assert result == "success"
        assert call_count == 3

    async def test_raises_after_max_attempts_exhausted(self):
        # Python 3.8 AsyncMock에는 __name__이 없어 retry 로그에서 AttributeError 발생.
        # 실제 async 함수로 대체.
        call_count = 0

        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("항상 실패")

        decorated = async_retry(max_attempts=3, delay=0.01)(always_fails)
        with pytest.raises(RuntimeError, match="항상 실패"):
            await decorated()
        assert call_count == 3

    async def test_does_not_retry_unlisted_exceptions(self):
        mock = AsyncMock(side_effect=KeyError("재시도 안 함"))
        decorated = async_retry(
            max_attempts=3, delay=0.01, exceptions=(ValueError,)
        )(mock)
        with pytest.raises(KeyError):
            await decorated()
        assert mock.call_count == 1

    async def test_retries_only_listed_exception(self):
        call_count = 0

        async def raises_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("재시도 대상")

        decorated = async_retry(
            max_attempts=3, delay=0.01, exceptions=(ValueError,)
        )(raises_value_error)
        with pytest.raises(ValueError):
            await decorated()
        assert call_count == 3

    async def test_backoff_multiplies_delay(self):
        sleep_calls: list[float] = []

        async def always_fails():
            raise ValueError("fail")

        with patch("asyncio.sleep", side_effect=lambda s: sleep_calls.append(s) or __import__("asyncio").sleep(0)):
            decorated = async_retry(
                max_attempts=4, delay=1.0, backoff=2.0
            )(always_fails)
            with pytest.raises(ValueError):
                await decorated()

        # 3번 재시도: 1.0 → 2.0 → 4.0
        assert len(sleep_calls) == 3
        assert sleep_calls[0] == pytest.approx(1.0)
        assert sleep_calls[1] == pytest.approx(2.0)
        assert sleep_calls[2] == pytest.approx(4.0)

    def test_preserves_original_function_name(self):
        async def my_function():
            pass

        decorated = async_retry()(my_function)
        assert decorated.__name__ == "my_function"

    async def test_passes_args_and_kwargs(self):
        async def add(a, b, *, multiplier=1):
            return (a + b) * multiplier

        decorated = async_retry()(add)
        result = await decorated(2, 3, multiplier=10)
        assert result == 50
