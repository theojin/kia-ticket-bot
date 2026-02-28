# KIA 타이거즈 티켓 자동구매 봇

> **잠실야구장** KIA 원정 경기 티켓을 NOL 티켓(구 인터파크)에서 자동으로 예매하는 봇입니다.

## ⚠️ 주의사항

- 이 프로그램은 **개인 학습 목적**으로 제작되었습니다.
- NOL 티켓 이용약관에 위반될 수 있습니다. **사용자 책임 하에** 사용하세요.
- `.env` 파일(개인정보, 카드정보)을 **절대 공유하거나 git에 커밋하지 마세요.**

---

## 주요 기능

- **자동 로그인**: 쿠키 세션 유지로 재실행 시 재로그인 불필요
- **정밀 타이밍**: NTP 시각 동기화, 오픈 시각 50ms 이내 정밀 클릭
- **좌석 우선순위 자동 선택**:
  1. 112, 113구역 (중앙 테이블석) 3석 — 최우선
  2. 318, 319구역 (중앙 네이비석)
  3. KIA 응원석 (3루 방향) 순차
- **카드 직접 입력 자동 결제**
- **Telegram + 소리 알림**: 대기열 진입, 좌석 선택, 예매 성공/실패 실시간 알림
- **봇 탐지 우회**: Patchright (CDP 레벨 패치) + 인간적 딜레이

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

## 빠른 시작

```powershell
# 1. 클론
git clone https://github.com/theojin/kia-ticket-bot.git
cd kia-ticket-bot

# 2. 가상환경 및 설치
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
patchright install chromium

# 3. 설정
copy .env.example .env
notepad .env   # 실제 값 입력

# 4. 실행
python main.py
```

자세한 설치 방법은 [docs/SETUP.md](docs/SETUP.md)를 참고하세요.

---

## 프로젝트 구조

```
kia-ticket-bot/
├── main.py              # 진입점
├── config.py            # 설정 로드 (.env)
├── src/
│   ├── browser/         # 브라우저 세션, 쿠키
│   ├── auth/            # 로그인, 세션 확인
│   ├── monitor/         # 타이밍 스케줄러, HTTP 폴링
│   ├── ticket/          # 페이지 이동, 좌석 선택, 결제
│   ├── notify/          # Telegram, 소리 알림
│   └── utils/           # 타이밍, 스크린샷, 재시도
├── docs/
│   ├── SETUP.md         # 설치 가이드
│   └── SEAT_MAP.md      # 잠실야구장 구역 맵
└── .env.example         # 설정 템플릿
```

---

## 라이선스

MIT License — [LICENSE](LICENSE) 참고
