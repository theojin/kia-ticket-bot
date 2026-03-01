# KIA 경기 일정 알리미

> KIA 타이거즈 원정 경기 일정을 모니터링하고, 예매 오픈 시 알림을 보내주는 개인용 도구입니다.

## 기능

- Chrome 프로필 기반 세션 관리
- 경기 일정 모니터링 및 Telegram 알림
- 예매 오픈 시각 타이머
- 스크린샷 캡처 및 전송

---

## 새 경기 설정하기

`.env` 파일에서 **3가지 정보**만 바꾸면 됩니다.

### Step 1. 경기 정보 찾기

팀 페이지 URL에서 코드를 확인합니다.

```
https://ticket.interpark.com/Contents/Sports/GoodsInfo?SportsCode=07002&TeamCode=PS113
```

| 값 | 위치 | 예시 |
|----|------|------|
| `SPORTS_CODE` | URL의 `SportsCode=` 뒤 | `07002` |
| `TEAM_CODE` | URL의 `TeamCode=` 뒤 | `PS113` |

### Step 2. GOODS_ID 찾기

1. 브라우저에서 `F12` → **Network** 탭 열기
2. "예매하기" 버튼을 **우클릭 → 요소 검사**
3. `onclick` 속성에서 `goodsCode=` 뒤의 숫자가 `GOODS_ID`

```html
<a onclick="...goodsCode=26001914...">예매하기</a>
```

### Step 3. .env 수정

```env
GOODS_ID=26001914
SALE_START_TIME=2026-04-15T10:00:00+09:00
SPORTS_CODE=07002
TEAM_CODE=PS113
```

### Step 4. 실행

```powershell
.venv\Scripts\activate
python main.py
```

---

## 설치

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
patchright install chromium
```

```powershell
copy .env.example .env
notepad .env
```

필수 설정:

| 항목 | 설명 |
|------|------|
| `GOODS_ID` | 상품 번호 |
| `SALE_START_TIME` | 오픈 시각 |
| `TELEGRAM_BOT_TOKEN` | Telegram 봇 토큰 |
| `TELEGRAM_CHAT_ID` | Telegram 채팅 ID |
| `SPORTS_CODE` | 스포츠 코드 |
| `TEAM_CODE` | 팀 코드 |

추가 설정:

| 항목 | 설명 | 기본값 |
|------|------|--------|
| `TICKET_ADULT` | 성인 매수 | `2` |
| `TICKET_CHILD` | 어린이 매수 | `1` |
| `BOOKER_BIRTH` | 생년월일 (YYMMDD) | |
| `BOOKER_PHONE` | 연락처 | |
| `BOOKER_EMAIL` | 이메일 | |

첫 실행 시 Chrome에서 직접 로그인하세요. 이후 세션이 유지됩니다.

---

## 프로젝트 구조

```
├── main.py              # 진입점
├── config.py            # 설정 로드
├── src/
│   ├── browser/         # 브라우저 세션
│   ├── auth/            # 세션 확인
│   ├── monitor/         # 스케줄러
│   ├── ticket/          # 페이지 처리
│   ├── notify/          # Telegram 알림
│   └── utils/           # 유틸리티
├── tests/               # 테스트
└── .env.example         # 설정 템플릿
```

---

## 문제 해결

| 증상 | 해결 |
|------|------|
| 로그인 실패 | 브라우저에서 직접 로그인 후 재실행 |
| Telegram 알림 없음 | 토큰/채팅 ID 확인 |

로그: `logs/` | 스크린샷: `screenshots/`
