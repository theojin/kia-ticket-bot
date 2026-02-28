"""
utils/retry.py - 재시도 데코레이터

네트워크 오류나 일시적 실패 시 지수 백오프(exponential backoff)로 재시도합니다.
"""

import asyncio
import functools
from typing import Callable, Type

from loguru import logger


def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
):
    """
    비동기 함수에 재시도 로직을 추가하는 데코레이터.

    Args:
        max_attempts: 최대 시도 횟수
        delay: 첫 재시도 전 대기 시간 (초)
        backoff: 재시도마다 대기 시간을 곱할 배수
        exceptions: 재시도할 예외 타입 목록
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} 최종 실패 "
                            f"({attempt}/{max_attempts}): {e}"
                        )
                        raise
                    logger.warning(
                        f"{func.__name__} 실패 ({attempt}/{max_attempts}), "
                        f"{current_delay:.1f}초 후 재시도: {e}"
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator
