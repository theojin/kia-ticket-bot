"""
notify/telegram.py - Telegram 봇 알림

예매 진행 상황을 실시간으로 Telegram으로 전송합니다.
"""

from telegram import Bot
from telegram.error import TelegramError
from loguru import logger

from config import Config


class Notifier:
    def __init__(self, config: Config):
        self.bot = Bot(token=config.telegram_bot_token)
        self.chat_id = config.telegram_chat_id

    async def _send(self, message: str) -> None:
        """메시지 전송. 실패해도 봇 동작은 계속됩니다."""
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message)
        except TelegramError as e:
            logger.warning(f"Telegram 전송 실패: {e}")

    async def notify_start(self, goods_id: str, sale_time: str) -> None:
        await self._send(
            f"KIA 티켓봇 시작\n"
            f"상품 ID: {goods_id}\n"
            f"오픈 시각: {sale_time}"
        )

    async def notify_login_success(self) -> None:
        await self._send("로그인 완료")

    async def notify_queue_entered(self) -> None:
        await self._send("대기열 진입 완료 - 좌석 선택 대기 중...")

    async def notify_seat_selected(self, section: str, quantity: int) -> None:
        await self._send(f"좌석 선택 완료: {section}구역 {quantity}석\n결제 진행 중...")

    async def notify_success(self, order_number: str) -> None:
        await self._send(
            f"예매 완료!\n"
            f"주문번호: {order_number}\n"
            f"NOL 티켓 앱에서 확인하세요."
        )

    async def notify_failure(self, reason: str) -> None:
        await self._send(f"예매 실패: {reason}")

    async def notify_stop_before_payment(self, section: str, quantity: int) -> None:
        await self._send(
            f"[테스트 모드] 결제 직전에서 일시 정지\n"
            f"구역: {section} / {quantity}석\n"
            f"터미널에서 Enter(진행) 또는 n(중단)을 입력하세요."
        )

    async def notify_manual_payment_needed(self) -> None:
        await self._send(
            "ISP/안심클릭 결제 감지!\n"
            "7분 안에 직접 결제를 완료하세요.\n"
            "브라우저 창을 확인하세요."
        )

    async def send_screenshot(self, path: str) -> None:
        """오류 스크린샷을 전송합니다."""
        try:
            with open(path, "rb") as f:
                await self.bot.send_photo(
                    chat_id=self.chat_id,
                    photo=f,
                    caption="오류 발생 스크린샷"
                )
        except Exception as e:
            logger.warning(f"스크린샷 전송 실패: {e}")
