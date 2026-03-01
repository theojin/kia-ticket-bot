"""
monitor/scheduler.py - 정밀 타이밍 스케줄러

티켓 오픈 시각 N초 전에 브라우저를 준비시키고,
오픈 시각에 맞춰 정밀하게 구매를 시도합니다.
"""

import asyncio
import contextlib
import ntplib
from datetime import datetime, timedelta, timezone
from typing import Callable, Awaitable

from loguru import logger

from config import Config
from src.monitor.poller import poll_until_open
from src.utils.timing import wait_until, seconds_until

KST = timezone(timedelta(hours=9))
NTP_SERVER = "pool.ntp.org"
MAX_CLOCK_OFFSET_MS = 500  # 500ms 이상 차이나면 경고


def check_clock_sync() -> float:
    """
    NTP 서버와 시각 편차를 확인합니다.

    Returns:
        클럭 편차 (초). 양수면 로컬이 빠름, 음수면 느림.
    """
    try:
        client = ntplib.NTPClient()
        response = client.request(NTP_SERVER, version=3)
        offset_ms = abs(response.offset * 1000)
        if offset_ms > MAX_CLOCK_OFFSET_MS:
            logger.warning(
                f"시각 편차가 큽니다: {offset_ms:.0f}ms "
                f"(권장: {MAX_CLOCK_OFFSET_MS}ms 이하)\n"
                f"Windows 시각 동기화: 작업 표시줄 > 날짜/시간 설정 > '지금 동기화'"
            )
        else:
            logger.info(f"시각 동기화 양호: 편차 {offset_ms:.0f}ms")
        return response.offset
    except Exception as e:
        logger.warning(f"NTP 동기화 확인 실패: {e}")
        return 0.0


async def run_at_sale_time(
    config: Config,
    on_prepare: Callable[[], Awaitable[None]],
    on_buy: Callable[[], Awaitable[bool]],
) -> bool:
    """
    티켓 오픈 시각에 맞춰 구매를 실행합니다.

    Args:
        config: 설정 객체
        on_prepare: 오픈 N초 전에 호출할 준비 함수 (브라우저 이동 등)
        on_buy: 오픈 시각에 호출할 구매 함수

    Returns:
        구매 성공 여부
    """
    sale_time = config.sale_start_time
    prepare_time = sale_time - timedelta(seconds=config.pre_sale_activate_seconds)

    now = datetime.now(tz=KST)
    remaining = seconds_until(sale_time)

    logger.info(
        f"오픈 시각: {sale_time.strftime('%Y-%m-%d %H:%M:%S KST')}\n"
        f"현재 시각: {now.strftime('%Y-%m-%d %H:%M:%S KST')}\n"
        f"남은 시간: {remaining:.1f}초"
    )

    if remaining < 0:
        logger.warning("이미 오픈 시각이 지났습니다. 즉시 구매를 시도합니다.")
        await on_prepare()
    else:
        # 준비 시각까지 대기
        if seconds_until(prepare_time) > 0:
            logger.info(f"{config.pre_sale_activate_seconds}초 전 준비 시각까지 대기...")
            await wait_until(prepare_time)

        # 브라우저 준비 (상품 페이지 이동)
        logger.info("브라우저 준비 시작...")
        await on_prepare()

        # 오픈 시각까지: 시각 기반 대기 + API 폴링을 병행 실행
        # 어느 쪽이든 먼저 완료되면 즉시 구매 시도
        if seconds_until(sale_time) > 0:
            logger.info("오픈 대기 중 (시각 기반 + API 폴링 병행)...")
            poll_task = asyncio.create_task(poll_until_open(config))
            time_task = asyncio.create_task(wait_until(sale_time))

            done, pending = await asyncio.wait(
                {poll_task, time_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            trigger = "API 폴링" if poll_task in done else "오픈 시각"
            logger.info(f"구매 트리거: {trigger}")

            for task in pending:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    # 구매 실행
    logger.info("구매 시도!")
    return await on_buy()
