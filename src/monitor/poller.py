"""
monitor/poller.py - 티켓 오픈 여부 HTTP 폴링

브라우저보다 가벼운 HTTP 요청으로 티켓 오픈 여부를 빠르게 감지합니다.
오픈이 감지되면 브라우저 레이어에 즉시 신호를 보냅니다.

NOTE: NOL 티켓 API 엔드포인트는 브라우저 DevTools Network 탭으로
      직접 확인 후 아래 상수를 업데이트해야 합니다.
"""

import asyncio

import httpx
from loguru import logger

from config import Config

# NOL 티켓 API 엔드포인트 (DevTools Network 탭으로 확인 필요)
# 예시: https://ticket.interpark.com/api/goods/{goods_id}/schedule
API_URL_TEMPLATE = "https://ticket.interpark.com/api/goods/{goods_id}/schedule"


def _is_sale_open(data: dict) -> bool:
    """
    API 응답을 분석해 티켓 판매가 시작되었는지 확인합니다.

    NOTE: 실제 응답 구조는 DevTools에서 확인 후 이 함수를 업데이트하세요.
    """
    # 실제 API 응답 필드명은 확인 후 수정 필요
    status = data.get("saleStatus") or data.get("status") or data.get("isSaleOpen")
    return status in (True, "OPEN", "ON_SALE", "sale")


async def poll_until_open(config: Config) -> bool:
    """
    API를 반복 폴링해 티켓 판매 시작을 감지합니다.

    Returns:
        True (오픈 감지 시)
    """
    url = API_URL_TEMPLATE.format(goods_id=config.goods_id)
    logger.info(f"티켓 오픈 폴링 시작: {url}")

    async with httpx.AsyncClient(timeout=5.0) as client:
        while True:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    if _is_sale_open(data):
                        logger.info("티켓 판매 오픈 감지!")
                        return True
            except httpx.RequestError as e:
                logger.debug(f"폴링 요청 오류 (재시도): {e}")
            except Exception as e:
                logger.warning(f"폴링 중 예상치 못한 오류: {e}")

            await asyncio.sleep(config.polling_interval)
