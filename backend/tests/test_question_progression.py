"""진행 순서 회귀 테스트: 메인 질문을 건너뛰고 파생질문부터 묻는 일이 없어야 한다."""

import pytest

SCRIPT = """
1. 요즘 어떤 AI 코딩 도구를 쓰시나요?
   [클로드] → 클로드를 고른 이유가 있을까요?
   [코덱스] → 코덱스를 고른 이유가 있을까요?
2. 그 도구를 하루에 얼마나 오래 쓰시나요?
   [3시간 이상] → 주로 어떤 작업에 그렇게 오래 쓰시나요?
"""


def _create_session(client) -> str:
    response = client.post(
        "/api/sessions",
        json={"title": "AI 도구 인터뷰", "duration_minutes": 20, "question_script": SCRIPT},
    )
    assert response.status_code == 201
    return response.json()["session"]["id"]


def _session_state(client, session_id: str) -> dict:
    response = client.get(f"/api/sessions/{session_id}")
    assert response.status_code == 200
    return response.json()["session"]


def test_첫_턴은_파생질문이_아니라_메인질문을_묻는다(client):
    session_id = _create_session(client)

    with client.websocket_connect(f"/ws/interview/{session_id}") as interviewee:
        assert interviewee.receive_json()["type"] == "session.state"
        client.post(f"/api/sessions/{session_id}/start")
        assert interviewee.receive_json()["session"]["status"] == "running"

        interviewee.send_json({"type": "utterance", "text": "안녕하세요, 잘 부탁드립니다."})
        first = interviewee.receive_json()

    assert first["type"] == "assistant.question"
    # 인사말 직후에는 1번 메인 질문이 나와야 한다. 파생질문("~고른 이유")이 먼저 나오면 안 된다.
    assert first["turn"]["text"] == "요즘 어떤 AI 코딩 도구를 쓰시나요?"
    assert "고른 이유" not in first["turn"]["text"]

    state = _session_state(client, session_id)
    # 메인 질문을 물었을 뿐 답변은 아직 받지 않았으므로 진행 위치는 그대로다.
    assert state["current_question_index"] == 0
    assert state["main_question_asked"] is True
    assert state["completed_question_indices"] == []


def test_메인질문_답변_이후에_파생질문이_나온다(client):
    session_id = _create_session(client)

    with client.websocket_connect(f"/ws/interview/{session_id}") as interviewee:
        interviewee.receive_json()
        client.post(f"/api/sessions/{session_id}/start")
        interviewee.receive_json()

        interviewee.send_json({"type": "utterance", "text": "안녕하세요."})
        main_question = interviewee.receive_json()["turn"]["text"]

        interviewee.send_json({"type": "utterance", "text": "저는 주로 클로드 씁니다."})
        follow_up = interviewee.receive_json()["turn"]["text"]

    assert main_question == "요즘 어떤 AI 코딩 도구를 쓰시나요?"
    # 답변에 등장한 갈래에 해당하는 파생질문이 이제서야 나온다
    assert follow_up == "클로드를 고른 이유가 있을까요?"

    state = _session_state(client, session_id)
    assert state["current_question_index"] == 0
    assert state["taken_branches"] == ["클로드"]


def test_다음_메인질문도_건너뛰지_않는다(client):
    session_id = _create_session(client)

    with client.websocket_connect(f"/ws/interview/{session_id}") as interviewee:
        interviewee.receive_json()
        client.post(f"/api/sessions/{session_id}/start")
        interviewee.receive_json()

        said = []
        for text in [
            "안녕하세요.",
            "저는 주로 클로드 씁니다.",
            "복잡한 리팩터링에 강해서요.",
            "하루에 3시간 이상은 쓰는 것 같아요.",
        ]:
            interviewee.send_json({"type": "utterance", "text": text})
            said.append(interviewee.receive_json()["turn"]["text"])

    # 1번 메인 -> 1번 파생 -> 2번 메인 -> 2번 파생 순서로 진행되어야 한다
    assert said == [
        "요즘 어떤 AI 코딩 도구를 쓰시나요?",
        "클로드를 고른 이유가 있을까요?",
        "그 도구를 하루에 얼마나 오래 쓰시나요?",
        "주로 어떤 작업에 그렇게 오래 쓰시나요?",
    ]

    state = _session_state(client, session_id)
    assert state["completed_question_indices"] == [0]
    assert state["current_question_index"] == 1


def test_참관자_지시_턴은_진행_위치를_넘기지_않는다(client):
    session_id = _create_session(client)

    with client.websocket_connect(f"/ws/observer/{session_id}") as observer:
        assert observer.receive_json()["type"] == "session.snapshot"

        with client.websocket_connect(f"/ws/interview/{session_id}") as interviewee:
            interviewee.receive_json()
            assert observer.receive_json()["type"] == "interviewee.connected"
            client.post(f"/api/sessions/{session_id}/start")
            interviewee.receive_json()
            observer.receive_json()

            observer.send_json({"type": "instruction.create", "text": "가격 얘기도 물어봐"})
            assert observer.receive_json()["type"] == "instruction.queued"

            interviewee.send_json({"type": "utterance", "text": "안녕하세요."})
            instructed = interviewee.receive_json()["turn"]["text"]

            interviewee.send_json({"type": "utterance", "text": "네, 가격은 괜찮습니다."})
            after = interviewee.receive_json()["turn"]["text"]

    assert "가격 얘기도 물어봐" in instructed
    # 지시 턴이 1번 메인 질문을 잡아먹으면 안 된다 — 다음 턴에 메인 질문이 그대로 나온다.
    assert after == "요즘 어떤 AI 코딩 도구를 쓰시나요?"


@pytest.mark.parametrize("asked", [True, False])
def test_렌더링이_메인질문_전달_여부에_따라_지침을_바꾼다(asked: bool):
    from app.services.question_script import parse_question_script, render_for_prompt

    nodes = parse_question_script(SCRIPT)
    text = render_for_prompt(nodes, current_index=0, main_question_asked=asked)

    if asked:
        assert "【★ 이번 턴에 진행할 질문 (이 질문만 다룰 것)】" in text
        assert "[미진행 파생질문]" in text
    else:
        assert "【★ 이번 턴에 반드시 할 일" in text
        # 아직 메인 질문 전이므로 파생질문을 고르라는 지침이 노출되면 안 된다
        assert "[미진행 파생질문]" not in text
        assert "지금 묻지 말 것" in text
