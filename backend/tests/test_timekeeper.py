"""타임키퍼: 남은 시간에 따라 파생질문을 켜고 끄고, 시간 초과를 잡아낸다.

실측 불만: 10분짜리 인터뷰가 6분에 끝나버리거나, 10분을 넘겨도 끝낼 기미가 없다.
"""

from datetime import timedelta

from app.schemas.session import QuestionNode, Session, utcnow
from app.services.ai.timekeeper import evaluate
from app.services.question_script import parse_question_script, render_for_prompt

SCRIPT = """
1. 요즘 어떤 AI 툴을 쓰시나요?
   [클로드] → 클로드를 고른 이유가 있을까요?
2. 하루에 얼마나 오래 쓰시나요?
   [3시간 이상] → 주로 어떤 작업에 쓰시나요?
3. 아쉬운 점이 있다면요?
"""


def _session(*, duration: int, elapsed_minutes: float, completed: list[int]) -> Session:
    nodes = parse_question_script(SCRIPT)
    return Session(
        title="타임키퍼 테스트",
        status="running",
        duration_minutes=duration,
        questions=nodes,
        completed_question_indices=completed,
        current_question_index=len(completed),
        started_at=utcnow() - timedelta(minutes=elapsed_minutes),
    )


def test_대본을_다_마쳐도_시간이_남으면_더_파라고_한다():
    signal = evaluate(_session(duration=10, elapsed_minutes=4, completed=[0, 1, 2]))

    assert signal.pace == "ahead"
    assert signal.should_deepen is True
    assert signal.allow_probes is True
    assert signal.should_move_on is False


def test_예정_시간을_넘기면_즉시_마무리_신호를_준다():
    signal = evaluate(_session(duration=10, elapsed_minutes=12, completed=[0, 1, 2]))

    assert signal.pace == "overtime"
    assert signal.should_move_on is True
    assert signal.allow_probes is False
    assert "즉시 마무리" in signal.hint


def test_시간을_넘겼는데_질문이_남으면_파생질문을_끈다():
    signal = evaluate(_session(duration=10, elapsed_minutes=11, completed=[0]))

    assert signal.pace == "overtime"
    assert signal.allow_probes is False
    assert "파생질문은 전부 건너뛰고" in signal.hint


def test_진도가_뒤처지면_파생질문을_끈다():
    # 10분 중 8분을 썼는데 3개 중 1개만 완료 -> 뒤처짐
    signal = evaluate(_session(duration=10, elapsed_minutes=8, completed=[0]))

    assert signal.pace == "behind"
    assert signal.allow_probes is False
    assert signal.should_move_on is True


def test_정상_페이스면_파생질문을_허용한다():
    # 10분 중 3분, 3개 중 1개 완료 -> 정상
    signal = evaluate(_session(duration=10, elapsed_minutes=3, completed=[0]))

    assert signal.pace == "on_track"
    assert signal.allow_probes is True
    assert signal.should_move_on is False


# =========================================================
# 프롬프트 렌더링에 실제로 반영되는가
# =========================================================

def test_시간이_빠듯하면_파생질문_지침_대신_건너뛰기_지침이_나간다():
    nodes = parse_question_script(SCRIPT)
    text = render_for_prompt(
        nodes,
        current_index=0,
        main_question_asked=True,
        main_question_answered=True,
        allow_probes=False,
        pace="behind",
    )

    assert "파생질문을 할 여유가 없습니다" in text
    assert "1개를 선택하여 질문하고" not in text


def test_대본을_마치고_시간이_남으면_미진행_파생질문을_제시한다():
    nodes = parse_question_script(SCRIPT)
    text = render_for_prompt(
        nodes,
        current_index=len(nodes),
        remaining_minutes=5,
        allow_probes=True,
        pace="ahead",
        covered_facts={"질문_1": "클로드 사용"},
    )

    assert "아직 묻지 않은 파생질문" in text
    assert "클로드를 고른 이유가 있을까요?" in text


def test_시간을_넘기면_대본_완료_후_즉시_마무리를_지시한다():
    nodes = parse_question_script(SCRIPT)
    text = render_for_prompt(
        nodes,
        current_index=len(nodes),
        remaining_minutes=0,
        allow_probes=False,
        pace="overtime",
        covered_facts={"질문_1": "클로드 사용"},
    )

    assert "예정 시간도 넘겼습니다" in text
    assert "아직 묻지 않은 파생질문" not in text
