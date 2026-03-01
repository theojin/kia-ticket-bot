"""
ticket/sports_booking.py - 스포츠 예매 전체 흐름

팝업(BookMain) 내부 iframe들을 제어하여 좌석 선택부터 결제 팝업까지 진행합니다.

흐름:
  1. BookSeatGate: 일반석 선택 → KBOGate.SetSeatAuto()
  2. BookPrice: 수량 선택 (성인 N매, 어린이 N매)
  3. fnNextStep() #1 → UserAgreePop 표시
  4. UserAgreePop: 약관 체크 → fnCheckAgree()
  5. fnNextStep() #2 → BookDelivery 표시
  6. BookDelivery: 생년월일, 연락처, 이메일 입력
  7. fnNextStep() #3 → BookPayment 표시
  8. BookPayment: 결제 정보 입력 (신용카드/삼성카드/일시불)
  9. fnNextStep() #4 → BookConfirm 표시
 10. BookConfirm: 취소수수료 동의 체크
 11. fnNextStep() #5 → 카드사 결제 팝업 표시
"""

from __future__ import annotations

import asyncio

from playwright.async_api import Page, Frame
from loguru import logger

from config import Config


async def _wait_for_frame(popup: Page, keyword: str, timeout: int = 15) -> Frame | None:
    """URL에 keyword가 포함된 프레임이 나타날 때까지 대기."""
    kw = keyword.lower()
    for _ in range(timeout):
        for frame in popup.frames:
            if kw in frame.url.lower():
                return frame
        await asyncio.sleep(1)
    return None


async def run_sports_booking(popup: Page, config: Config) -> Page | None:
    """
    스포츠 예매 팝업에서 좌석 선택 → 수량 → 약관 → 배송정보 → 결제 → 팝업까지 진행.

    Args:
        popup: navigate_to_goods()가 반환한 팝업 Page
        config: 설정 객체

    Returns:
        카드사 결제 팝업 Page (성공 시) 또는 None (실패 시)
    """
    # dialog 핸들러 등록 (alert 자동 수락)
    popup.on("dialog", lambda d: asyncio.ensure_future(d.accept()))

    # 1. 좌석 등급 선택 + 자동배정
    grade_name = await _select_seat_grade(popup, config)
    if not grade_name:
        return None

    # 2. 수량 선택
    if not await _select_ticket_quantity(popup, config):
        return None

    # 3. fnNextStep #1 → 약관 동의 팝업 표시
    logger.info("다음 단계 #1...")
    await popup.main_frame.evaluate("fnNextStep()")
    await asyncio.sleep(3)

    # 4. 약관 동의 + 저장
    if not await _agree_terms(popup):
        return None

    # 5. fnNextStep #2 → 배송/예매자 정보 화면
    logger.info("다음 단계 #2...")
    await popup.main_frame.evaluate("fnNextStep()")
    await asyncio.sleep(3)

    # 6. 예매자 정보 입력
    if not await _fill_delivery_info(popup, config):
        return None

    # 7. fnNextStep #3 → 결제 화면
    logger.info("다음 단계 #3 (결제 진입)...")
    await popup.main_frame.evaluate("fnNextStep()")
    await asyncio.sleep(3)

    logger.info("결제 화면 도달!")

    # 8. 결제 정보 입력
    if not await _fill_payment_info(popup, config):
        return None

    # 9. fnNextStep #4 → 주문 확인/취소수수료 동의 화면
    logger.info("다음 단계 #4 (주문 확인)...")
    await popup.main_frame.evaluate("fnNextStep()")
    await asyncio.sleep(3)

    # 10. 취소수수료 동의 체크
    if not await _agree_cancel_policy(popup):
        return None

    # 11. fnNextStep #5 → 카드사 결제 팝업
    logger.info("다음 단계 #5 (결제하기)...")

    # 결제 팝업 감지 준비 (이니시스 등 카드사 인증 창)
    payment_popup = None
    try:
        async with popup.expect_popup(timeout=15000) as popup_info:
            await popup.main_frame.evaluate("fnNextStep()")
        payment_popup = await popup_info.value
        logger.info(f"카드사 결제 팝업 열림: {payment_popup.url[:100]}")
    except Exception as e:
        logger.warning(f"결제 팝업 감지 타임아웃 (iframe 방식일 수 있음): {e}")

    await asyncio.sleep(3)
    logger.info("결제 요청 완료!")

    # 팝업 감지 성공 시 팝업 반환, 실패 시 booking 페이지 반환
    return payment_popup or popup


async def _select_seat_grade(popup: Page, config: Config) -> str | None:
    """BookSeatGate에서 일반석 선택 + 자동배정."""
    seat_frame = await _wait_for_frame(popup, "BookSeatGate")
    if not seat_frame:
        logger.error("BookSeatGate 프레임 없음")
        return None

    # 잔여석 있는 첫 번째 일반석 (자동배정 가능) 선택
    target = await seat_frame.evaluate("""() => {
        for (const a of document.querySelectorAll('.groundList .list a[gc]')) {
            if (a.getAttribute('sgn').includes('일반석')
                && a.getAttribute('as') === 'Y'
                && parseInt(a.getAttribute('rc')) > 0) {
                return {
                    sg: a.getAttribute('sg'),
                    gc: a.getAttribute('gc'),
                    sgn: a.getAttribute('sgn'),
                    rc: a.getAttribute('rc'),
                };
            }
        }
        return null;
    }""")

    if not target:
        logger.error("일반석 잔여석 없음")
        return None

    logger.info(f"좌석 등급 선택: {target['sgn']} (잔여 {target['rc']}석)")
    await seat_frame.locator(
        f"a[sg='{target['sg']}'][gc='{target['gc']}']"
    ).click()
    await asyncio.sleep(2)

    # 자동배정 실행
    await seat_frame.evaluate("KBOGate.SetSeatAuto()")
    logger.info("자동배정 실행")
    await asyncio.sleep(3)

    return target['sgn']


async def _select_ticket_quantity(popup: Page, config: Config) -> bool:
    """BookPrice에서 성인/어린이 수량 선택."""
    price_frame = await _wait_for_frame(popup, "BookPrice")
    if not price_frame:
        logger.error("BookPrice 프레임 없음")
        return False

    adult = config.ticket_adult
    child = config.ticket_child

    result = await price_frame.evaluate(f"""() => {{
        let adultSet = false, childSet = false;
        for (const sel of document.querySelectorAll('select')) {{
            const row = sel.closest('tr');
            if (!row) continue;
            const t = row.textContent;
            if (t.includes('예매가/성인')
                && !t.includes('할인') && !t.includes('카드') && !t.includes('누리')) {{
                sel.value = '{adult}';
                sel.dispatchEvent(new Event('change', {{ bubbles: true }}));
                adultSet = true;
            }} else if (t.includes('예매가/어린이')
                && !t.includes('할인') && !t.includes('카드') && !t.includes('누리')) {{
                sel.value = '{child}';
                sel.dispatchEvent(new Event('change', {{ bubbles: true }}));
                childSet = true;
            }}
        }}
        return {{ adultSet, childSet }};
    }}""")

    logger.info(f"수량 선택: 성인 {adult}매, 어린이 {child}매 (결과: {result})")
    await asyncio.sleep(2)
    return True


async def _agree_terms(popup: Page) -> bool:
    """UserAgreePop에서 약관 동의 체크 + 저장."""
    agree_frame = await _wait_for_frame(popup, "useragree", timeout=10)
    if not agree_frame:
        agree_frame = await _wait_for_frame(popup, "certify", timeout=5)

    if not agree_frame:
        logger.warning("약관 프레임 없음 - 이미 동의 완료된 것으로 간주")
        return True

    # 체크박스 상태 확인
    state = await agree_frame.evaluate("""() => {
        const cb = document.getElementById('Agree');
        return cb ? { exists: true, checked: cb.checked } : { exists: false };
    }""")

    if not state.get('exists'):
        logger.warning("약관 체크박스 없음")
        return True

    if not state.get('checked'):
        # 체크박스 체크
        await agree_frame.evaluate("""() => {
            document.getElementById('Agree').checked = true;
        }""")
        await asyncio.sleep(1)

    # fnCheckAgree() 호출 (저장)
    try:
        await agree_frame.evaluate("fnCheckAgree()")
        logger.info("약관 동의 + 저장 완료")
    except Exception as e:
        logger.error(f"fnCheckAgree 실패: {e}")
        return False

    await asyncio.sleep(2)
    return True


async def _fill_delivery_info(popup: Page, config: Config) -> bool:
    """BookDelivery에서 예매자 정보 입력 (생년월일, 연락처, 이메일)."""
    delivery_frame = await _wait_for_frame(popup, "BookDelivery")
    if not delivery_frame:
        logger.error("BookDelivery 프레임 없음")
        return False

    # 입력 필드 목록 확인 및 입력
    try:
        # 생년월일
        birth = config.booker_birth
        if birth:
            await delivery_frame.evaluate(f"""() => {{
                const inputs = document.querySelectorAll('input');
                for (const inp of inputs) {{
                    const row = inp.closest('tr');
                    if (row && row.textContent.includes('생년월일')) {{
                        inp.value = '{birth}';
                        inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        break;
                    }}
                }}
            }}""")
            logger.info(f"생년월일 입력: {birth}")

        # 연락처 (3개 필드로 나뉘어 있을 수 있음)
        phone = config.booker_phone
        if phone:
            parts = phone.replace("-", " ").split()
            if len(parts) == 3:
                await delivery_frame.evaluate(f"""() => {{
                    const inputs = document.querySelectorAll('input[type="text"], input[type="tel"], input:not([type])');
                    const phoneInputs = [];
                    let foundPhone = false;
                    for (const inp of inputs) {{
                        const row = inp.closest('tr');
                        if (row && row.textContent.includes('연락처')) {{
                            phoneInputs.push(inp);
                        }}
                    }}
                    if (phoneInputs.length >= 3) {{
                        phoneInputs[0].value = '{parts[0]}';
                        phoneInputs[1].value = '{parts[1]}';
                        phoneInputs[2].value = '{parts[2]}';
                        phoneInputs.forEach(inp => {{
                            inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }});
                    }}
                }}""")
                logger.info(f"연락처 입력: {parts[0]}-****-{parts[2]}")

        # 이메일
        email = config.booker_email
        if email:
            await delivery_frame.evaluate(f"""() => {{
                const inputs = document.querySelectorAll('input');
                for (const inp of inputs) {{
                    const row = inp.closest('tr');
                    if (row && row.textContent.includes('이메일')) {{
                        inp.value = '{email}';
                        inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        break;
                    }}
                }}
            }}""")
            logger.info(f"이메일 입력: {email}")

    except Exception as e:
        logger.error(f"예매자 정보 입력 실패: {e}")
        return False

    await asyncio.sleep(2)
    return True


async def _fill_payment_info(popup: Page, config: Config) -> bool:
    """BookPayment에서 결제 정보 입력 (신용카드/삼성카드/일시불)."""
    pay_frame = await _wait_for_frame(popup, "BookPayment", timeout=10)
    if not pay_frame:
        logger.error("BookPayment 프레임 없음")
        return False

    try:
        # 결제방식=신용카드, 결제수단=일반신용카드는 기본 선택되어 있음
        # 카드종류: '삼성' 텍스트를 가진 옵션을 찾아 선택
        samsung_value = await pay_frame.evaluate("""() => {
            const sel = document.getElementById('DiscountCard');
            if (!sel) return null;
            for (const opt of sel.options) {
                if (opt.textContent.includes('삼성')) {
                    return opt.value;
                }
            }
            return null;
        }""")

        if not samsung_value:
            logger.error("삼성카드 옵션을 찾을 수 없음")
            return False

        # onchange="fnCardSelect(this.value)" 핸들러를 직접 호출
        await pay_frame.evaluate(f"""() => {{
            const sel = document.getElementById('DiscountCard');
            if (sel) {{
                sel.value = '{samsung_value}';
                if (typeof fnCardSelect === 'function') {{
                    fnCardSelect('{samsung_value}');
                }}
            }}
        }}""")
        logger.info(f"카드 선택 시도: 삼성카드 (value={samsung_value})")
        await asyncio.sleep(2)

        # 선택 결과 확인
        card = await pay_frame.evaluate(
            "document.getElementById('DiscountCard')?.selectedOptions[0]?.textContent?.trim()"
        )
        halbu = await pay_frame.evaluate(
            "document.getElementById('HalbuMonth')?.selectedOptions[0]?.textContent?.trim()"
        )
        logger.info(f"결제 정보: {card} / {halbu}")

        if card and '삼성' not in card:
            logger.warning(f"삼성카드 선택 실패 - 현재 선택: {card}, 재시도...")
            # 재시도: selectedIndex 방식
            await pay_frame.evaluate("""() => {
                const sel = document.getElementById('DiscountCard');
                if (!sel) return;
                for (let i = 0; i < sel.options.length; i++) {
                    if (sel.options[i].textContent.includes('삼성')) {
                        sel.selectedIndex = i;
                        if (typeof fnCardSelect === 'function') {
                            fnCardSelect(sel.options[i].value);
                        }
                        break;
                    }
                }
            }""")
            await asyncio.sleep(2)
            card = await pay_frame.evaluate(
                "document.getElementById('DiscountCard')?.selectedOptions[0]?.textContent?.trim()"
            )
            logger.info(f"재시도 후 카드: {card}")

    except Exception as e:
        logger.error(f"결제 정보 입력 실패: {e}")
        return False

    return True


async def _agree_cancel_policy(popup: Page) -> bool:
    """BookConfirm에서 취소수수료/취소기한 동의 체크."""
    confirm_frame = await _wait_for_frame(popup, "BookConfirm", timeout=10)
    if not confirm_frame:
        logger.error("BookConfirm 프레임 없음")
        return False

    try:
        # 취소수수료 동의 체크박스 (id=CancelAgree)
        state = await confirm_frame.evaluate("""() => {
            const cb = document.getElementById('CancelAgree');
            return cb ? { exists: true, checked: cb.checked } : { exists: false };
        }""")

        if not state.get('exists'):
            logger.warning("취소수수료 동의 체크박스 없음")
            return True

        if not state.get('checked'):
            await confirm_frame.evaluate("""() => {
                const cb = document.getElementById('CancelAgree');
                if (cb) cb.checked = true;
            }""")
            await asyncio.sleep(1)

        logger.info("취소수수료/취소기한 동의 완료")

    except Exception as e:
        logger.error(f"취소수수료 동의 실패: {e}")
        return False

    return True
