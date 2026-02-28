"""
utils/timing.py - 인간적 딜레이 및 정밀 타이밍 유틸리티

봇 탐지를 피하기 위해 랜덤한 지연을 추가하고,
티켓 오픈 시각에 정밀하게 클릭할 수 있도록 지원합니다.
"""

import asyncio
import random
from datetime import datetime, timezone


async def human_delay(min_sec: float = 0.3, max_sec: float = 1.2) -> None:
    """인간적인 랜덤 딜레이. 봇 탐지 우회용."""
    await asyncio.sleep(random.uniform(min_sec, max_sec))


def random_typing_speed() -> int:
    """키 입력 간격 (ms). 인간적인 타이핑 속도 시뮬레이션."""
    return random.randint(50, 150)


async def wait_until(target_time: datetime, check_interval: float = 0.01) -> None:
    """
    지정된 시각까지 대기합니다.
    - 2초 이상 남았을 때: 100ms 간격으로 대기
    - 2초 미만: 정밀 busy-wait (10ms 간격)
    """
    while True:
        now = datetime.now(tz=target_time.tzinfo or timezone.utc)
        remaining = (target_time - now).total_seconds()

        if remaining <= 0:
            break
        elif remaining > 2.0:
            await asyncio.sleep(0.1)
        else:
            await asyncio.sleep(check_interval)


def seconds_until(target_time: datetime) -> float:
    """현재 시각 기준 target_time까지 남은 초."""
    now = datetime.now(tz=target_time.tzinfo or timezone.utc)
    return (target_time - now).total_seconds()
