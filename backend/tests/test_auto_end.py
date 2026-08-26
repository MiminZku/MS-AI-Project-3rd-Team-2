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

def test_마무리는_대기_안내_후_작별인사로_끝난다(client):
    session_id = _create_session(client)

    with client.websocket_connect(f"/ws/interview/{session_id}") as interviewee:
        _start(client, session_id, interviewee)
        said = _run_to_farewell(interviewee)

        # 곧바로 작별하지 않고 "리서치팀 확인" 안내가 먼저 나가야 한다
        assert "잠시 확인해 보겠습니다" in said[-1]

        # 대기 시간이 지나면 작별 인사가 나가고 ended 상태가 전파된다
        farewell = interviewee.receive_json()
        ended_state = interviewee.receive_json()

    assert farewell["type"] == "assistant.question"
    assert "인터뷰를 마치겠습니다" in farewell["turn"]["text"]
    assert ended_state["type"] == "session.state"
    assert ended_state["session"]["status"] == "ended"
    assert _session(client, session_id)["status"] == "ended"


def test_종료된_뒤에는_추가_발화에도_질문이_생성되지_않는다(client):
    session_id = _create_session(client)

    with client.websocket_connect(f"/ws/interview/{session_id}") as interviewee:
        _start(client, session_id, interviewee)
        _run_to_farewell(interviewee)
        interviewee.receive_json()  # 작별 인사
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


def test_대기창_중_들어온_지시는_질문으로_나가고_종료되지_않는다(client, monkeypatch):
    """마무리 대기창 동안 참관자가 지시를 넣으면 그 질문을 하고 인터뷰가 이어져야 한다."""
    from app.core.config import get_settings

    # 지시를 넣을 시간을 확보하기 위해 대기창을 넉넉히 연다
    monkeypatch.setattr(get_settings(), "final_instruction_window_seconds", 10)

    session_id = _create_session(client)

    with client.websocket_connect(f"/ws/observer/{session_id}") as observer:
        assert observer.receive_json()["type"] == "session.snapshot"

        with client.websocket_connect(f"/ws/interview/{session_id}") as interviewee:
            interviewee.receive_json()
            assert observer.receive_json()["type"] == "interviewee.connected"
            client.post(f"/api/sessions/{session_id}/start")
            interviewee.receive_json()

            said = _run_to_farewell(interviewee)
            assert "잠시 확인해 보겠습니다" in said[-1]

            # 대기창이 열린 동안 참관자가 추가 지시를 넣는다
            observer.send_json({"type": "instruction.create", "text": "가격 얘기도 물어봐"})

            extra_question = interviewee.receive_json()

    assert extra_question["type"] == "assistant.question"
    assert "가격 얘기도 물어봐" in extra_question["turn"]["text"]

    session = _session(client, session_id)
    assert session["status"] == "running"
    # 지시를 하나 처리했으니 다음 마무리 때 대기창을 한 번 더 열 수 있어야 한다
    assert session["final_check_done"] is False
