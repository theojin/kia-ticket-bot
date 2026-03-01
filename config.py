"""
config.py - 설정 로드 및 유효성 검사

.env 파일에서 모든 설정을 로드합니다.
필수 항목이 누락된 경우 프로그램 시작 시 즉시 오류를 발생시킵니다.
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



@dataclass
class Config:
    # 대상 티켓
    goods_id: str
    sale_start_time: datetime
    preferred_sections: list[str]
    max_tickets: int

    # Telegram
    telegram_bot_token: str
    telegram_chat_id: str

    # 스포츠 티켓 (선택사항 - 설정 시 스포츠 플로우 사용)
    sports_code: str  # 예: "07002" (축구), 빈 문자열이면 일반 플로우
    team_code: str  # 예: "PS113" (충남아산FC), 빈 문자열이면 일반 플로우

    # 스포츠 예매 정보
    ticket_adult: int  # 성인 매수
    ticket_child: int  # 어린이 매수
    booker_birth: str  # 예매자 생년월일 (YYMMDD)
    booker_phone: str  # 예매자 연락처 (010-XXXX-XXXX)
    booker_email: str  # 예매자 이메일

    # 동작 설정
    polling_interval: float
    pre_sale_activate_seconds: int
    headless: bool
    screenshot_on_error: bool
    stop_before_payment: bool  # True이면 결제 직전에 사용자 확인 후 진행

    @property
    def is_sports(self) -> bool:
        """스포츠 티켓 플로우 사용 여부."""
        return bool(self.sports_code and self.team_code)

    def __post_init__(self):
        if self.max_tickets < 1 or self.max_tickets > 4:
            raise ValueError("MAX_TICKETS는 1~4 사이여야 합니다.")
        if self.polling_interval < 0.1:
            raise ValueError("POLLING_INTERVAL_SECONDS는 0.1 이상이어야 합니다.")
        if bool(self.sports_code) != bool(self.team_code):
            raise ValueError(
                "SPORTS_CODE와 TEAM_CODE는 함께 설정하거나 둘 다 비워야 합니다."
            )

    def summary(self) -> str:
        """설정 요약 (민감정보 마스킹 처리)."""
        return (
            f"[설정 요약]\n"
            f"  모드: {'스포츠' if self.is_sports else '일반'}\n"
            f"  상품 ID: {self.goods_id}\n"
            + (f"  스포츠 코드: {self.sports_code}\n"
               f"  팀 코드: {self.team_code}\n" if self.is_sports else "")
            + f"  오픈 시각: {self.sale_start_time.isoformat()}\n"
            f"  선호 구역: {', '.join(self.preferred_sections)}\n"
            f"  예매 매수: {self.max_tickets}매\n"
            f"  Telegram: {'설정됨' if self.telegram_bot_token else '미설정'}\n"
            f"  Headless: {self.headless}\n"
            f"  결제 전 확인: {'ON (테스트 모드)' if self.stop_before_payment else 'OFF'}\n"
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
        goods_id=_require("GOODS_ID"),
        sale_start_time=sale_start_time,
        preferred_sections=preferred_sections,
        max_tickets=int(os.getenv("MAX_TICKETS", "3")),
        telegram_bot_token=_require("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_require("TELEGRAM_CHAT_ID"),
        polling_interval=float(os.getenv("POLLING_INTERVAL_SECONDS", "0.5")),
        pre_sale_activate_seconds=int(os.getenv("PRE_SALE_ACTIVATE_SECONDS", "30")),
        headless=os.getenv("HEADLESS", "false").lower() == "true",
        screenshot_on_error=os.getenv("SCREENSHOT_ON_ERROR", "true").lower() == "true",
        stop_before_payment=os.getenv("STOP_BEFORE_PAYMENT", "false").lower() == "true",
        sports_code=os.getenv("SPORTS_CODE", ""),
        team_code=os.getenv("TEAM_CODE", ""),
        ticket_adult=int(os.getenv("TICKET_ADULT", "2")),
        ticket_child=int(os.getenv("TICKET_CHILD", "1")),
        booker_birth=os.getenv("BOOKER_BIRTH", ""),
        booker_phone=os.getenv("BOOKER_PHONE", ""),
        booker_email=os.getenv("BOOKER_EMAIL", ""),
    )
