"""AI가 작별 인사를 하면 참관자가 종료 버튼을 누른 것과 동일하게 자동 종료되어야 한다."""

from app.schemas.session import Instruction, QuestionNode, Session
from app.services.ai.llm import GeneratedQuestion
from app.services.orchestrator import _should_auto_end
from app.services.store import InMemoryStore

SCRIPT = "1. 요즘 어떤 AI 코딩 도구를 쓰시나요?"


def _create_session(client) -> str:
    response = client.post(
        "/api/sessions",
        json={"title": "자동 종료 인터뷰", "duration_minutes": 20, "question_script": SCRIPT},
    )
    assert response.status_code == 201
    return response.json()["session"]["id"]


def _session(client, session_id: str) -> dict:
    return client.get(f"/api/sessions/{session_id}").json()["session"]


def _start(client, session_id: str, interviewee) -> None:
    interviewee.receive_json()
    client.post(f"/api/sessions/{session_id}/start")
    interviewee.receive_json()


def _run_to_farewell(interviewee) -> list[str]:
    """메인 질문 -> 마무리 확인 -> 작별 인사까지 대본을 끝까지 진행시킨다."""
    said = []
    for text in ["안녕하세요.", "클로드 씁니다.", "아니요, 더 없습니다."]:
        interviewee.send_json({"type": "utterance", "text": text})
        said.append(interviewee.receive_json()["turn"]["text"])
    return said


# =========================================================
# 자동 종료 조건 판단 (단위)
# =========================================================

def _closing_session() -> Session:
    """대본을 모두 마친(current_question_index == 질문 수) 세션."""
    return Session(
        title="자동 종료 인터뷰",
        status="running",
        questions=[QuestionNode(id="q1", order=1, text="요즘 어떤 AI 코딩 도구를 쓰시나요?")],
        current_question_index=1,
        main_question_asked=True,
    )


def _farewell() -> GeneratedQuestion:
    return GeneratedQuestion(
        text="오늘 인터뷰를 모두 마치겠습니다. 감사합니다!",
        rationale="[END]",
        next_question_index=1,
        is_closing=True,
    )


async def test_지시_큐가_비어있으면_자동_종료_대상이다():
    store = InMemoryStore()
    session = _closing_session()
    await store.save_session(session)

    assert await _should_auto_end(session, _farewell(), store) is True


async def test_대기중인_참관자_지시가_있으면_자동_종료하지_않는다():
    store = InMemoryStore()
    session = _closing_session()
    await store.save_session(session)
    await store.push_instruction(Instruction(session_id=session.id, text="가격도 물어봐"))

    assert await _should_auto_end(session, _farewell(), store) is False


async def test_대본이_남아있으면_종료_신호가_있어도_자동_종료하지_않는다():
    store = InMemoryStore()
    session = _closing_session()
    session.current_question_index = 0
    await store.save_session(session)

    assert await _should_auto_end(session, _farewell(), store) is False


async def test_작별_인사가_아니면_자동_종료하지_않는다():
    store = InMemoryStore()
    session = _closing_session()
    await store.save_session(session)

    still_asking = GeneratedQuestion(
        text="혹시 더 하고 싶은 말씀 있으실까요?",
        rationale="",
        next_question_index=1,
        is_closing=False,
    )

    assert await _should_auto_end(session, still_asking, store) is False


# =========================================================
# 실제 인터뷰 흐름 (통합)
# =========================================================

def test_작별인사_이후_세션이_자동_종료된다(client):
    session_id = _create_session(client)

    with client.websocket_connect(f"/ws/interview/{session_id}") as interviewee:
        _start(client, session_id, interviewee)
        said = _run_to_farewell(interviewee)

        # 작별 인사 직후 인터뷰이에게 ended 상태가 전파되어야 메인룸이 종료 화면으로 넘어간다
        ended_state = interviewee.receive_json()

    assert "인터뷰를 모두 마치겠습니다" in said[-1]
    assert ended_state["type"] == "session.state"
    assert ended_state["session"]["status"] == "ended"
    assert _session(client, session_id)["status"] == "ended"


def test_종료된_뒤에는_추가_발화에도_질문이_생성되지_않는다(client):
    session_id = _create_session(client)

    with client.websocket_connect(f"/ws/interview/{session_id}") as interviewee:
        _start(client, session_id, interviewee)
        _run_to_farewell(interviewee)
        assert interviewee.receive_json()["session"]["status"] == "ended"

        transcript_before = client.get(f"/api/sessions/{session_id}/transcript").json()

        # 종료 직후 마이크가 한 번 더 열려 발화가 들어와도 새 질문을 만들지 않는다
        interviewee.send_json({"type": "utterance", "text": "아 저기요, 하나만 더요."})

    transcript_after = client.get(f"/api/sessions/{session_id}/transcript").json()
    assert len(transcript_after) == len(transcript_before)


def test_대본_도중에는_종료_신호가_와도_인터뷰가_계속된다(client, monkeypatch):
    """모델이 중간에 잘못 is_closing을 켜도 대본이 남아 있으면 인터뷰가 이어져야 한다."""
    from app.services.ai import llm

    session_id = _create_session(client)
    original = llm.StubQuestionGenerator.generate

    async def always_closing(self, session, transcript, instruction, timekeeper_hint=None):
        generated = await original(self, session, transcript, instruction, timekeeper_hint)
        generated.is_closing = True
        return generated

    monkeypatch.setattr(llm.StubQuestionGenerator, "generate", always_closing)

    with client.websocket_connect(f"/ws/interview/{session_id}") as interviewee:
        _start(client, session_id, interviewee)

        # 1번 메인 질문을 전달하는 턴 — 대본이 아직 남았으므로 종료되면 안 된다
        interviewee.send_json({"type": "utterance", "text": "안녕하세요."})
        interviewee.receive_json()

    assert _session(client, session_id)["status"] == "running"
