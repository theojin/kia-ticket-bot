"""
notify/sound.py - 로컬 소리 알림

PC 앞에 있을 때 중요 이벤트를 소리로 알려줍니다.
playsound3 라이브러리 사용. 오류 발생 시 조용히 무시합니다.
"""

import asyncio

from loguru import logger

# 알림음 파일 경로 (없으면 시스템 비프음 사용)
SOUND_FILES = {
    "success": None,        # 예매 성공음 (MP3 파일 경로 설정 가능)
    "failure": None,        # 예매 실패음
    "queue": None,          # 대기열 진입음
    "payment_manual": None, # 수동 결제 필요 알림음
}


async def play_alert(event: str) -> None:
    """
    이벤트에 맞는 소리를 재생합니다.

    Args:
        event: 'success', 'failure', 'queue', 'payment_manual' 중 하나
    """
    try:
        sound_file = SOUND_FILES.get(event)

        loop = asyncio.get_running_loop()

        if sound_file:
            # 사용자 정의 소리 파일 재생 (blocking이므로 executor에서 실행)
            from playsound3 import playsound
            await loop.run_in_executor(None, lambda: playsound(sound_file, block=True))
        else:
            # 시스템 기본 비프음 (Windows) — blocking이므로 executor에서 실행
            import winsound
            frequency = {
                "success": 1000,
                "failure": 400,
                "queue": 800,
                "payment_manual": 600,
            }.get(event, 800)
            duration = 500  # ms

            # 반복 횟수
            repeat = 3 if event in ("success", "payment_manual") else 1
            for _ in range(repeat):
                await loop.run_in_executor(None, winsound.Beep, frequency, duration)

    except Exception as e:
        logger.debug(f"소리 알림 재생 실패 (무시): {e}")
