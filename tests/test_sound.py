"""tests/test_sound.py - notify/sound.py 유닛 테스트"""

from unittest.mock import MagicMock, patch

import pytest

from src.notify.sound import play_alert


class TestPlayAlert:
    async def test_all_events_complete_without_error(self):
        """모든 이벤트 타입에서 예외 없이 완료되어야 함."""
        with patch("winsound.Beep"):
            for event in ("success", "failure", "queue", "payment_manual"):
                await play_alert(event)

    async def test_unknown_event_does_not_raise(self):
        """알 수 없는 이벤트도 조용히 무시해야 함."""
        with patch("winsound.Beep"):
            await play_alert("unknown_event_xyz")

    async def test_success_uses_1000hz(self):
        beep_calls: list[tuple] = []

        def capture_beep(freq, dur):
            beep_calls.append((freq, dur))

        with patch("winsound.Beep", side_effect=capture_beep):
            await play_alert("success")

        assert all(freq == 1000 for freq, _ in beep_calls)
        assert len(beep_calls) > 0

    async def test_failure_uses_400hz(self):
        beep_calls: list[tuple] = []

        def capture_beep(freq, dur):
            beep_calls.append((freq, dur))

        with patch("winsound.Beep", side_effect=capture_beep):
            await play_alert("failure")

        assert beep_calls == [(400, 500)]

    async def test_queue_uses_800hz(self):
        beep_calls: list[tuple] = []

        def capture_beep(freq, dur):
            beep_calls.append((freq, dur))

        with patch("winsound.Beep", side_effect=capture_beep):
            await play_alert("queue")

        assert beep_calls == [(800, 500)]

    async def test_success_beeps_three_times(self):
        beep_calls: list = []

        def capture_beep(freq, dur):
            beep_calls.append(freq)

        with patch("winsound.Beep", side_effect=capture_beep):
            await play_alert("success")

        assert len(beep_calls) == 3

    async def test_payment_manual_beeps_three_times(self):
        beep_calls: list = []

        def capture_beep(freq, dur):
            beep_calls.append(freq)

        with patch("winsound.Beep", side_effect=capture_beep):
            await play_alert("payment_manual")

        assert len(beep_calls) == 3

    async def test_failure_beeps_once(self):
        beep_calls: list = []

        def capture_beep(freq, dur):
            beep_calls.append(freq)

        with patch("winsound.Beep", side_effect=capture_beep):
            await play_alert("failure")

        assert len(beep_calls) == 1

    async def test_beep_exception_silently_ignored(self):
        """winsound.Beep가 실패해도 봇이 계속 실행되어야 함."""
        with patch("winsound.Beep", side_effect=OSError("beep 실패")):
            await play_alert("success")  # 예외 없이 완료되어야 함
