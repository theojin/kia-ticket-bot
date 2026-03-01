# 설치 및 실행 가이드

## 요구사항

- Python 3.11 이상
- Windows 10/11 (소리 알림은 Windows 전용)
- NOL 티켓 계정 (ticket.interpark.com)
- Telegram 계정 및 봇 토큰

---

## 1단계: Python 설치 확인

PowerShell에서 실행:
```powershell
python --version
```
`Python 3.11.x` 이상이면 됩니다. 없으면 [python.org](https://python.org)에서 설치.

---

## 2단계: 프로젝트 다운로드

```powershell
cd C:\Users\theoj\git
git clone https://github.com/theojin/kia-ticket-bot.git
cd kia-ticket-bot
```

---

## 3단계: 가상환경 생성 및 라이브러리 설치

```powershell
python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
patchright install chromium
```

---

## 4단계: .env 설정

```powershell
copy .env.example .env
notepad .env
```

`.env` 파일을 열어 아래 항목을 실제 값으로 채우세요:

| 항목 | 설명 |
|------|------|
| `GOODS_ID` | 티켓 URL의 상품번호 (예: `ticket.interpark.com/goods/`**`12345678`**) |
| `SALE_START_TIME` | 티켓 오픈 시각 (예: `2026-04-01T10:00:00+09:00`) |
| `PREFERRED_SECTIONS` | 선호 구역 (기본값: `112,113,318,319,KIA_3루`) |
| `MAX_TICKETS` | 예매 매수 (기본값: `3`) |
| `TELEGRAM_BOT_TOKEN` | Telegram 봇 토큰 |
| `TELEGRAM_CHAT_ID` | Telegram 채팅 ID |

> **주의**: `.env` 파일은 절대 다른 사람과 공유하거나 git에 커밋하지 마세요.

---

## 5단계: Telegram 봇 설정

1. Telegram에서 `@BotFather` 검색
2. `/newbot` 명령 → 봇 이름 입력 → 토큰 발급
3. 발급된 토큰을 `.env`의 `TELEGRAM_BOT_TOKEN`에 입력
4. `@userinfobot` 검색 → `/start` → 내 chat_id 확인
5. chat_id를 `.env`의 `TELEGRAM_CHAT_ID`에 입력

---

## 6단계: 실행

```powershell
.venv\Scripts\activate
python main.py
```

봇이 시작되면 Telegram으로 알림이 옵니다.
티켓 오픈 시각까지 PC를 켜두세요.

---

## 좌석 맵 선택자 설정 (첫 실행 전 필수)

`docs/SEAT_MAP.md`를 참고해 잠실야구장 좌석 선택자를 확인하고
`src/ticket/seat_selector.py`의 선택자를 업데이트해야 합니다.

---

## 문제 해결

| 증상 | 해결 방법 |
|------|----------|
| 로그인 실패 | `src/auth/login.py`의 선택자 확인, NOL 티켓 사이트 변경 여부 확인 |
| 구매 버튼 못 찾음 | `src/ticket/navigator.py` 선택자 업데이트 |
| 좌석 선택 실패 | `docs/SEAT_MAP.md` 참고, `seat_selector.py` 선택자 업데이트 |
| 결제 창 오류 | 카드사 결제 팝업(이니시스) 확인, 팝업 차단 설정 확인 |

로그 파일: `logs/bot_YYYYMMDD.log`
오류 스크린샷: `screenshots/` 폴더
