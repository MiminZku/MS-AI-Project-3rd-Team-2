"""세션 종료는 리포트 생성 없이 완료 상태만 저장한다."""


SCRIPT = "1. 배달앱을 얼마나 자주 쓰시나요?\n2. 최소주문금액에 대해 어떻게 느끼시나요?"


def _create_session(client) -> str:
    response = client.post(
        "/api/sessions",
        json={"title": "리포트 테스트", "duration_minutes": 20, "question_script": SCRIPT},
    )
    return response.json()["session"]["id"]


def test_세션_종료시_자동_개별리포트를_생성하지_않는다(client):

    session_id = _create_session(client)

    with client.websocket_connect(f"/ws/interview/{session_id}") as interviewee:
        assert interviewee.receive_json()["type"] == "session.state"
        start_response = client.post(f"/api/sessions/{session_id}/start")
        assert start_response.status_code == 200
        assert interviewee.receive_json()["session"]["status"] == "running"
        interviewee.send_json({"type": "utterance", "text": "일주일에 세 번 정도 씁니다."})
        assert interviewee.receive_json()["type"] == "assistant.question"

    end_response = client.post(f"/api/sessions/{session_id}/end")
    assert end_response.status_code == 200
    assert end_response.json()["status"] == "ended"

        # 세션 단위 리포트 폴링은 더 이상 생성 트리거가 아니다.
    assert client.get(f"/api/sessions/{session_id}/report").status_code == 202


