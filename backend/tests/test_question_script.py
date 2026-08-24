from app.services.question_script import parse_question_script, render_for_prompt

SCRIPT = """
1. 배달앱을 얼마나 자주 쓰시나요?
2. 최소주문금액에 대해 어떻게 느끼시나요?
   [부담됨] → 그 때문에 주문을 포기한 경험이 있나요?
   [보통]   -> 최소주문금액을 맞추려고 더 시킨 적은 있나요?
"""


def test_메인질문과_분기를_파싱한다():
    nodes = parse_question_script(SCRIPT)

    assert [n.order for n in nodes] == [1, 2]
    assert nodes[0].text == "배달앱을 얼마나 자주 쓰시나요?"
    assert nodes[0].branches == {}
    assert nodes[1].branches["부담됨"] == "그 때문에 주문을 포기한 경험이 있나요?"
    # 화살표는 → 와 -> 둘 다 허용
    assert nodes[1].branches["보통"] == "최소주문금액을 맞추려고 더 시킨 적은 있나요?"


def test_빈_스크립트는_빈_리스트():
    assert parse_question_script("") == []


def test_프롬프트_렌더링에_현재위치가_표시된다():
    # render_for_prompt는 이제 완료/현재/예정 질문을 섹션으로 분리해서 렌더링한다
    # (기존 "번호. 텍스트 <== 현재 진행 중" 한 줄짜리 포맷에서 강민기님이 변경한 구조).
    text = render_for_prompt(parse_question_script(SCRIPT), current_index=1)
    lines = text.splitlines()

    assert "【이미 완료된 질문 (다시 묻거나 언급 금지)】" in text
    assert any(line.startswith("✓ [완료] 1. ") for line in lines)

    assert "【★ 이번 턴에 진행할 질문 (이 질문만 다룰 것)】" in text
    current_line = next(line for line in lines if line.startswith("▶ [index: 1]"))
    assert "2. " in current_line

    assert "[갈래: 부담됨]" in text
