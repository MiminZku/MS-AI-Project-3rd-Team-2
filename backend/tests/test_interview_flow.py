"""핵심 차별점(§4.1) 회귀 테스트: 참관자 지시가 다음 질문에 반영되고 1회만 소비된다."""

SCRIPT = """
1. 배달앱을 얼마나 자주 쓰시나요?
2. 최소주문금액에 대해 어떻게 느끼시나요?
   [부담됨] → 그 때문에 주문을 포기한 경험이 있나요?
"""


def _create_session(client) -> str:
    response = client.post(
        "/api/sessions",
        json={"title": "배달앱 인터뷰", "duration_minutes": 20, "question_script": SCRIPT},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["interviewee_url"].endswith(body["session"]["id"])
    return body["session"]["id"]


def test_헬스체크(client):
    assert client.get("/health").json()["status"] == "ok"


def test_참관자_지시가_다음_질문에_주입되고_한_번만_소비된다(client):
    session_id = _create_session(client)

    with client.websocket_connect(f"/ws/observer/{session_id}") as observer:
        assert observer.receive_json()["type"] == "session.snapshot"

        observer.send_json({"type": "instruction.create", "text": "경쟁사 대비 장점을 물어봐"})
        queued = observer.receive_json()
        assert queued["type"] == "instruction.queued"
        assert queued["instruction"]["status"] == "queued"

        with client.websocket_connect(f"/ws/interview/{session_id}") as interviewee:
            assert interviewee.receive_json()["type"] == "session.state"
            assert observer.receive_json()["type"] == "interviewee.connected"

            interviewee.send_json({"type": "utterance", "text": "일주일에 세 번 정도 씁니다."})

            question = interviewee.receive_json()
            assert question["type"] == "assistant.question"
            # C5: 판단 근거는 인터뷰이에게 절대 나가지 않는다
            assert "rationale" not in question["turn"]
            assert "경쟁사 대비 장점을 물어봐" in question["turn"]["text"]

            observer_events = [observer.receive_json() for _ in range(3)]
            types = [event["type"] for event in observer_events]
            assert types == ["transcript.append", "transcript.append", "instruction.applied"]
            # 참관자에게는 근거가 보인다
            assert observer_events[1]["turn"]["rationale"]
            assert observer_events[2]["instruction"]["status"] == "applied"

            # 두 번째 턴: 큐가 비었으므로 지시 재주입 없이 질문 리스트로 진행 (C4)
            interviewee.send_json({"type": "utterance", "text": "그건 좀 부담됐어요."})
            second = interviewee.receive_json()
            assert second["type"] == "assistant.question"
            assert "경쟁사 대비 장점을 물어봐" not in second["turn"]["text"]

    instructions = client.get(f"/api/sessions/{session_id}/instructions").json()
    assert len(instructions) == 1
    assert instructions[0]["status"] == "applied"


def test_없는_세션은_소켓이_거부된다(client):
    import pytest
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/interview/ses_존재하지않음") as ws:
            ws.receive_json()
