"""
config.py - 설정 로드 및 유효성 검사

.env 파일에서 모든 설정을 로드합니다.
필수 항목이 누락된 경우 프로그램 시작 시 즉시 오류를 발생시킵니다.
민감정보(카드번호 등)는 이 파일에 직접 작성하지 마세요.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    """필수 환경변수 로드. 없으면 즉시 오류."""
    value = os.getenv(key)
    if not value:
        raise ValueError(
            f"필수 환경변수 '{key}'가 설정되지 않았습니다. "
            f".env.example을 참고해 .env 파일을 설정하세요."
        )
    return value


def _mask(value: str, visible: int = 4) -> str:
    """민감정보 마스킹 (로그 출력용)."""
    if len(value) <= visible:
        return "****"
    return value[:visible] + "*" * (len(value) - visible)


@dataclass
class Config:
    # NOL 티켓 계정
    interpark_id: str
    interpark_pw: str

    # 대상 티켓
    goods_id: str
    sale_start_time: datetime
    preferred_sections: list[str]
    max_tickets: int

    # 결제 정보
    card_number: str
    card_expiry: str
    card_cvv: str
    card_password_2digits: str

    # Telegram
    telegram_bot_token: str
    telegram_chat_id: str

    # 동작 설정
    polling_interval: float
    pre_sale_activate_seconds: int
    headless: bool
    screenshot_on_error: bool

    def __post_init__(self):
        if self.max_tickets < 1 or self.max_tickets > 4:
            raise ValueError("MAX_TICKETS는 1~4 사이여야 합니다.")
        if self.polling_interval < 0.1:
            raise ValueError("POLLING_INTERVAL_SECONDS는 0.1 이상이어야 합니다.")

    def summary(self) -> str:
        """설정 요약 (민감정보 마스킹 처리)."""
        return (
            f"[설정 요약]\n"
            f"  계정: {_mask(self.interpark_id)}\n"
            f"  상품 ID: {self.goods_id}\n"
            f"  오픈 시각: {self.sale_start_time.isoformat()}\n"
            f"  선호 구역: {', '.join(self.preferred_sections)}\n"
            f"  예매 매수: {self.max_tickets}매\n"
            f"  카드: {_mask(self.card_number)} (****)\n"
            f"  Telegram: {'설정됨' if self.telegram_bot_token else '미설정'}\n"
            f"  Headless: {self.headless}\n"
        )


def load_config() -> Config:
    """환경변수에서 Config 객체를 생성하고 유효성을 검사합니다."""
    sale_start_raw = _require("SALE_START_TIME")
    try:
        sale_start_time = datetime.fromisoformat(sale_start_raw)
    except ValueError:
        raise ValueError(
            f"SALE_START_TIME 형식이 잘못되었습니다: '{sale_start_raw}'\n"
            f"올바른 형식 예시: 2026-04-01T10:00:00+09:00"
        )

    sections_raw = _require("PREFERRED_SECTIONS")
    preferred_sections = [s.strip() for s in sections_raw.split(",") if s.strip()]

    return Config(
        interpark_id=_require("INTERPARK_ID"),
        interpark_pw=_require("INTERPARK_PW"),
        goods_id=_require("GOODS_ID"),
        sale_start_time=sale_start_time,
        preferred_sections=preferred_sections,
        max_tickets=int(os.getenv("MAX_TICKETS", "3")),
        card_number=_require("CARD_NUMBER"),
        card_expiry=_require("CARD_EXPIRY"),
        card_cvv=_require("CARD_CVV"),
        card_password_2digits=_require("CARD_PASSWORD_2DIGITS"),
        telegram_bot_token=_require("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_require("TELEGRAM_CHAT_ID"),
        polling_interval=float(os.getenv("POLLING_INTERVAL_SECONDS", "0.5")),
        pre_sale_activate_seconds=int(os.getenv("PRE_SALE_ACTIVATE_SECONDS", "30")),
        headless=os.getenv("HEADLESS", "false").lower() == "true",
        screenshot_on_error=os.getenv("SCREENSHOT_ON_ERROR", "true").lower() == "true",
    )
