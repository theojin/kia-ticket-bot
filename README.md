# KIA 타이거즈 티켓 자동구매 봇

> **잠실야구장** KIA 원정 경기 티켓을 NOL 티켓(구 인터파크)에서 자동으로 예매하는 봇입니다.

## 주의사항

- 이 프로그램은 **개인 학습 목적**으로 제작되었습니다.
- NOL 티켓 이용약관에 위반될 수 있습니다. **사용자 책임 하에** 사용하세요.
- `.env` 파일(개인정보)을 **절대 공유하거나 git에 커밋하지 마세요.**

---

## 주요 기능

- **자동 로그인**: Chrome 프로필 세션 유지로 재로그인 불필요
- **정밀 타이밍**: NTP 시각 동기화, 오픈 시각 50ms 이내 정밀 클릭
- **좌석 우선순위 자동 선택**: 설정한 구역 순서대로 자동 시도
- **결제 자동 진행**: 좌석 선택 → 약관 동의 → 배송 정보 → 카드 선택 → 카드사 결제창까지 자동
- **Telegram + 소리 알림**: 대기열 진입, 좌석 선택, 결제 단계별 실시간 알림
- **봇 탐지 우회**: Patchright (CDP 레벨 패치) + 인간적 딜레이

---

## 새 경기 예매하기 (핵심 가이드)

새로운 스포츠 경기의 티켓을 예매하려면 `.env` 파일에서 **3가지 정보**만 바꾸면 됩니다.

### Step 1. 경기 정보 찾기

NOL 티켓 사이트에서 원하는 팀의 경기 목록 페이지로 이동합니다.

```
https://ticket.interpark.com/Contents/Sports/GoodsInfo?SportsCode=07002&TeamCode=PS113
```

이 URL에서 두 가지 값을 확인합니다:

| 값 | 위치 | 예시 |
|----|------|------|
| `SPORTS_CODE` | URL의 `SportsCode=` 뒤 | `07002` (축구/야구 등) |
| `TEAM_CODE` | URL의 `TeamCode=` 뒤 | `PS113` (충남아산FC 등) |

> 이미 같은 팀이면 이 값은 바꿀 필요 없습니다.

### Step 2. GOODS_ID 찾기

경기 목록에서 원하는 경기의 **"예매하기" 버튼**을 찾습니다.

1. 브라우저에서 `F12` (개발자 도구) → **Network** 탭 열기
2. "예매하기" 버튼을 **우클릭 → 요소 검사**
3. 버튼의 `onclick` 속성에서 `goodsCode=` 뒤의 숫자가 `GOODS_ID`입니다

```html
<!-- 예시 -->
<a onclick="...goodsCode=26001914...">예매하기</a>
                         ^^^^^^^^
                         이 숫자가 GOODS_ID
```

### Step 3. .env 수정

`.env` 파일에서 아래 3개 값만 업데이트합니다:

```env
# 이 3개만 바꾸면 됩니다!
GOODS_ID=26001914
SALE_START_TIME=2026-04-15T10:00:00+09:00
SPORTS_CODE=07002
TEAM_CODE=PS113
```

- `GOODS_ID`: Step 2에서 찾은 상품 번호
- `SALE_START_TIME`: 티켓 오픈(판매 시작) 시각 (ISO 8601 형식)

### Step 4. 실행

```powershell
.venv\Scripts\activate
python main.py
```

봇이 자동으로:
1. Chrome 브라우저를 열고 로그인 확인
2. 오픈 시각까지 대기
3. 오픈 시각에 자동으로 좌석 선택 → 예매 → 결제 화면까지 진행
4. 카드사 결제 팝업이 열리면 **Telegram으로 알림** 전송
5. 사용자가 브라우저에서 직접 결제 완료

---

## 처음 설치하기

### 1. Python 설치

```powershell
python --version   # Python 3.11 이상 필요
```

### 2. 프로젝트 클론 및 설치

```powershell
git clone https://github.com/theojin/kia-ticket-bot.git
cd kia-ticket-bot

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
patchright install chromium
```

### 3. .env 설정

```powershell
copy .env.example .env
notepad .env
```

필수 설정 항목:

| 항목 | 설명 |
|------|------|
| `GOODS_ID` | 티켓 상품 번호 |
| `SALE_START_TIME` | 티켓 오픈 시각 (예: `2026-04-01T10:00:00+09:00`) |
| `TELEGRAM_BOT_TOKEN` | Telegram 봇 토큰 ([설정 방법](docs/SETUP.md#5단계-telegram-봇-설정)) |
| `TELEGRAM_CHAT_ID` | Telegram 채팅 ID |
| `SPORTS_CODE` | 스포츠 코드 (예: `07002`) |
| `TEAM_CODE` | 팀 코드 (예: `PS113`) |

스포츠 예매 추가 항목:

| 항목 | 설명 | 기본값 |
|------|------|--------|
| `TICKET_ADULT` | 성인 매수 | `2` |
| `TICKET_CHILD` | 어린이 매수 | `1` |
| `BOOKER_BIRTH` | 예매자 생년월일 (YYMMDD) | |
| `BOOKER_PHONE` | 예매자 연락처 (010-XXXX-XXXX) | |
| `BOOKER_EMAIL` | 예매자 이메일 | |

### 4. 첫 실행 (로그인)

첫 실행 시 Chrome 브라우저가 열리면 **NOL 티켓에 직접 로그인**하세요.
로그인 정보는 Chrome 프로필에 저장되므로 이후에는 자동으로 유지됩니다.

```powershell
python main.py
```

---

## 테스트 모드

실제 결제 전에 흐름을 확인하고 싶으면:

```env
STOP_BEFORE_PAYMENT=true
```

카드사 결제 팝업이 열린 시점에서 멈추고 Telegram 알림을 보냅니다.
브라우저에서 직접 결제하거나 닫으면 됩니다.

---

## 프로젝트 구조

```
kia-ticket-bot/
├── main.py              # 진입점
├── config.py            # 설정 로드 (.env)
├── src/
│   ├── browser/         # 브라우저 세션 (Chrome CDP)
│   ├── auth/            # 로그인 세션 확인
│   ├── monitor/         # 타이밍 스케줄러, HTTP 폴링
│   ├── ticket/          # 페이지 이동, 좌석 선택, 결제
│   ├── notify/          # Telegram, 소리 알림
│   └── utils/           # 타이밍, 스크린샷, 재시도
├── tests/               # 유닛 테스트
├── docs/
│   ├── SETUP.md         # 상세 설치 가이드
│   └── SEAT_MAP.md      # 잠실야구장 구역 맵
└── .env.example         # 설정 템플릿
```

---

## 기술 스택

| 역할 | 라이브러리 |
|------|-----------|
| 브라우저 자동화 | [Patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright-python) |
| 타이밍 스케줄러 | APScheduler |
| HTTP 폴링 | httpx |
| Telegram 알림 | python-telegram-bot |
| 로깅 | loguru |

---

## 문제 해결

| 증상 | 해결 방법 |
|------|----------|
| 로그인 실패 | 브라우저에서 NOL 티켓에 직접 로그인 후 재실행 |
| 좌석 선택 실패 | `PREFERRED_SECTIONS` 구역명 확인 |
| 결제 팝업 안 열림 | Chrome 팝업 차단 설정 확인 |
| Telegram 알림 없음 | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` 확인 |

로그 파일: `logs/bot_YYYYMMDD.log`
오류 스크린샷: `screenshots/` 폴더

---

## 라이선스

MIT License — [LICENSE](LICENSE) 참고
