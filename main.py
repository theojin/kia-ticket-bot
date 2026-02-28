"""
main.py - KIA 티켓 자동구매 봇 진입점

실행 방법:
    python main.py

실행 전 .env 파일을 설정하세요. (.env.example 참고)
"""

import asyncio
import sys
from datetime import timedelta

from loguru import logger

from config import load_config
from src.browser.session import create_session, close_session
from src.auth.verify import ensure_logged_in
from src.monitor.scheduler import run_at_sale_time, check_clock_sync
from src.ticket.navigator import navigate_to_goods, click_buy_button, wait_for_queue
from src.ticket.seat_selector import select_seats
from src.ticket.payment import complete_payment
from src.notify.telegram import Notifier
from src.notify.sound import play_alert
from src.utils.screenshot import take_screenshot

# 로그 설정
logger.remove()
logger.add(sys.stdout, level="INFO", colorize=True,
           format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")
logger.add("logs/bot_{time:YYYYMMDD}.log", level="DEBUG", rotation="1 day",
           retention="7 days", encoding="utf-8")


async def main():
    # 1. 설정 로드 및 검증
    logger.info("=" * 50)
    logger.info("KIA 티켓 자동구매 봇 시작")
    logger.info("=" * 50)

    try:
        config = load_config()
    except ValueError as e:
        logger.error(f"설정 오류: {e}")
        sys.exit(1)

    logger.info(config.summary())

    # 2. 시각 동기화 확인
    check_clock_sync()

    # 3. 알림 초기화
    notifier = Notifier(config)

    # 4. 브라우저 세션 생성
    browser, context, page = await create_session(config)

    try:
        # 5. 로그인 확인
        logged_in = await ensure_logged_in(page, config)
        if not logged_in:
            logger.error("로그인 실패. 봇을 종료합니다.")
            await notifier.notify_failure("로그인 실패")
            return

        await notifier.notify_login_success()
        await play_alert("queue")

        await notifier.notify_start(
            config.goods_id,
            config.sale_start_time.strftime("%Y-%m-%d %H:%M:%S KST")
        )

        # 6. 오픈 시각에 맞춰 구매 실행
        async def on_prepare():
            """오픈 N초 전: 상품 페이지로 이동"""
            await navigate_to_goods(page, config)

        async def on_buy() -> bool:
            """오픈 시각: 구매 버튼 클릭 → 대기열 → 좌석 선택 → 결제"""
            # 구매 버튼 클릭
            if not await click_buy_button(page):
                await notifier.notify_failure("구매 버튼 클릭 실패")
                return False

            await notifier.notify_queue_entered()

            # 대기열 통과 대기
            if not await wait_for_queue(page):
                await notifier.notify_failure("대기열 타임아웃")
                return False

            # 좌석 선택
            section_used = await select_seats(page, config)
            if not section_used:
                screenshot_path = await take_screenshot(page, "seat_fail")
                await notifier.notify_failure("좌석 선택 실패 (전 구역 매진)")
                if screenshot_path:
                    await notifier.send_screenshot(screenshot_path)
                return False

            await notifier.notify_seat_selected(section_used, config.max_tickets)

            # 결제
            order_number = await complete_payment(page, config, notifier)
            if order_number:
                await notifier.notify_success(order_number)
                await play_alert("success")
                logger.info(f"예매 완료! 주문번호: {order_number}")
                return True
            else:
                await notifier.notify_failure("결제 실패")
                await play_alert("failure")
                return False

        success = await run_at_sale_time(config, on_prepare, on_buy)

        if success:
            logger.info("봇 정상 종료 (예매 성공)")
        else:
            logger.warning("봇 종료 (예매 실패)")

    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}")
        screenshot_path = await take_screenshot(page, "crash")
        await notifier.notify_failure(f"예상치 못한 오류: {e}")
        if screenshot_path:
            await notifier.send_screenshot(screenshot_path)
        raise

    finally:
        await close_session(browser)


if __name__ == "__main__":
    asyncio.run(main())
