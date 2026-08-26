"""응답자가 실제로 '답변'하기 전에는 파생질문으로 넘어가면 안 된다.

실측 회귀 케이스: 첫 메인 질문(AI 툴 조합)을 물었는데 응답자가
"김재현 아니고 강민식이고요. AI 엔지니어로 일하고 있습니다"라고 이름만 정정했다.
질문에 대한 답은 하나도 안 했는데 AI가 파생질문(심화 질문)으로 넘어가버렸다.
"""

from app.schemas.session import QuestionNode, Session
from app.services.question_script import parse_question_script, render_for_prompt

SCRIPT = """
1. 요즘 어떤 AI 툴 조합을 쓰고 계신가요?
   [클로드] → 클로드를 고른 이유가 있을까요?
   [코덱스] → 코덱스를 고른 이유가 있을까요?
2. 하루에 얼마나 오래 쓰시나요?
"""


def _create_session(client) -> str:
    response = client.post(
        "/api/sessions",
        json={"title": "AI 툴 인터뷰", "duration_minutes": 20, "question_script": SCRIPT},
    )
    assert response.status_code == 201
    return response.json()["session"]["id"]


def _session(client, session_id: str) -> dict:
    return client.get(f"/api/sessions/{session_id}").json()["session"]


# =========================================================
# 프롬프트 렌더링 (단위)
# =========================================================

def test_묻기만_하고_답변_전이면_파생질문_지침이_안_나온다():
    nodes = parse_question_script(SCRIPT)
    text = render_for_prompt(
        nodes, current_index=0, main_question_asked=True, main_question_answered=False
    )

    assert "메인 질문의 답변 받아내기" in text
    # 답변을 받았다고 단정하거나 파생질문을 고르라고 시키면 안 된다
    assert "메인 질문 답변 수신 상태" not in text
    assert "[미진행 파생질문]" not in text
    assert "지금 묻지 말 것" in text


def test_답변을_받은_뒤에야_파생질문_지침이_나온다():
    nodes = parse_question_script(SCRIPT)
    text = render_for_prompt(
        nodes, current_index=0, main_question_asked=True, main_question_answered=True
    )

    assert "[미진행 파생질문]" in text
    assert "메인 질문 답변 받아내기" not in text


# =========================================================
# 실제 인터뷰 흐름 (통합)
# =========================================================

def _patch_answer_flag(monkeypatch, is_answer: bool):
    """스텁이 '이번 발화는 답변이 아니다'라고 신고하도록 만든다."""
    from app.services.ai import llm

    original = llm.StubQuestionGenerator.generate

    async def patched(self, session, transcript, instruction, timekeeper_hint=None):
        generated = await original(self, session, transcript, instruction, timekeeper_hint)
        generated.is_answer_to_current_question = is_answer
        return generated

    monkeypatch.setattr(llm.StubQuestionGenerator, "generate", patched)


def test_답변이_아니면_파생질문으로_넘어가지_않는다(client, monkeypatch):
    session_id = _create_session(client)

    with client.websocket_connect(f"/ws/interview/{session_id}") as interviewee:
        interviewee.receive_json()
        client.post(f"/api/sessions/{session_id}/start")
        interviewee.receive_json()

        # 1턴: 메인 질문 전달
        interviewee.send_json({"type": "utterance", "text": "안녕하세요."})
        main_question = interviewee.receive_json()["turn"]["text"]

        state = _session(client, session_id)
        assert state["main_question_asked"] is True
        assert state["main_question_answered"] is False

        # 2턴: 질문에 답하지 않고 이름만 정정 -> 파생질문으로 넘어가면 안 된다
        _patch_answer_flag(monkeypatch, is_answer=False)
        interviewee.send_json(
            {"type": "utterance", "text": "김재현 아니고 강민식이고요. AI 엔지니어로 일하고 있습니다."}
        )
        interviewee.receive_json()

    assert main_question == "요즘 어떤 AI 툴 조합을 쓰고 계신가요?"

    state = _session(client, session_id)
    assert state["current_question_index"] == 0
    assert state["main_question_answered"] is False
    # 파생질문을 소비하거나 질문을 완료 처리하면 안 된다
    assert state["taken_branches"] == []
    assert state["completed_question_indices"] == []
    # 답변이 아닌 발화에서 뽑은 내용을 "확보된 사실"로 박제하지 않는다
    assert state["covered_facts"] == {}


def test_뒤늦게_답변하면_그때_파생질문으로_넘어간다(client, monkeypatch):
    session_id = _create_session(client)

    with client.websocket_connect(f"/ws/interview/{session_id}") as interviewee:
        interviewee.receive_json()
        client.post(f"/api/sessions/{session_id}/start")
        interviewee.receive_json()

        interviewee.send_json({"type": "utterance", "text": "안녕하세요."})
        interviewee.receive_json()

        _patch_answer_flag(monkeypatch, is_answer=False)
        interviewee.send_json({"type": "utterance", "text": "김재현 아니고 강민식입니다."})
        interviewee.receive_json()

        # 이제 진짜로 질문에 답한다
        _patch_answer_flag(monkeypatch, is_answer=True)
        interviewee.send_json({"type": "utterance", "text": "클로드 위주로 씁니다."})
        follow_up = interviewee.receive_json()["turn"]["text"]

    assert follow_up == "클로드를 고른 이유가 있을까요?"

    state = _session(client, session_id)
    assert state["main_question_answered"] is True
    assert state["taken_branches"] == ["클로드"]


# =========================================================
# 참관자 지시가 대본 지침에 묻히지 않는가 (실측 회귀)
# =========================================================

def test_지시가_있으면_대본_행동지침이_렌더링되지_않는다():
    """지시 턴에 '파생질문 1개를 골라라' 같은 강한 대본 지침이 같이 나가면 모델이 지시를 무시한다."""
    from app.services.question_script import parse_question_script, render_for_prompt

    nodes = parse_question_script(SCRIPT)
    text = render_for_prompt(
        nodes,
        current_index=0,
        main_question_asked=True,
        main_question_answered=True,
        pending_instruction="자기소개 다시 물어봐주세요",
    )

    assert "참관자 지시 수행" in text
    assert "자기소개 다시 물어봐주세요" in text
    # 대본 행동 지침은 이번 턴에 나가면 안 된다
    assert "[미진행 파생질문]" not in text
    assert "1개를 선택하여 질문하고" not in text


def test_지시_텍스트가_시스템_프롬프트에_두_번_들어간다():
    """상단 지령 주입 + 진행 현황 블록 양쪽에 있어야 대본 지침에 묻히지 않는다."""
    from app.schemas.session import Instruction, Session
    from app.services.ai.prompts import build_system_prompt
    from app.services.question_script import parse_question_script

    session = Session(
        title="지시 반영 테스트",
        status="running",
        questions=parse_question_script(SCRIPT),
        current_question_index=0,
        main_question_asked=True,
        main_question_answered=True,
    )
    instruction = Instruction(session_id=session.id, text="자기소개 다시 물어봐주세요")

    prompt = build_system_prompt(session, instruction)

    assert prompt.count("자기소개 다시 물어봐주세요") >= 2
    # 진행 현황 블록의 대본 행동 지침(파생질문 고르기)은 이번 턴에 렌더링되면 안 된다.
    # ("[미진행 파생질문]"이라는 표현 자체는 BASE_SYSTEM_PROMPT 규칙 설명에도 등장하므로
    #  렌더링된 지침 문구로 확인한다.)
    assert "1개를 선택하여 질문하고" not in prompt
    assert "이번 턴에는 대본의 다음 질문이나 파생질문으로 넘어가지 마라" in prompt
