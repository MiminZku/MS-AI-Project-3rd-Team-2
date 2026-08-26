"""실시간 지시는 세션을 만든 PM만 보낼 수 있어야 한다.

클라이언트는 프로젝트 Access ID로 백룸에 참관만 할 수 있고, 지시 큐에는 손댈 수 없다.
UI에서 숨기는 것만으로는 부족해서 서버에서도 막는다.
"""

from app.services.client_project_access import issue_client_project_token


def _create_project_session(client) -> tuple[str, str]:
    """프로젝트(Study)에 속한 세션을 만들고 (session_id, study_id)를 돌려준다."""
    study = client.post(
        "/api/projects",
        json={
            "title": "클라이언트 권한 테스트",
            "research_purpose": "권한 분리 확인",
            "question_script": "1. 요즘 어떤 AI 도구를 쓰시나요?",
        },
    )
    assert study.status_code == 201, study.text
    study_id = study.json()["study"]["id"]

    session = client.post(
        "/api/sessions",
        json={"study_id": study_id, "title": "P01", "duration_minutes": 20},
    )
    assert session.status_code == 201
    return session.json()["session"]["id"], study_id


def test_pm은_지시를_보낼_수_있다(client):
    session_id, _ = _create_project_session(client)

    with client.websocket_connect(f"/ws/observer/{session_id}") as observer:
        snapshot = observer.receive_json()
        assert snapshot["type"] == "session.snapshot"
        assert snapshot["viewer_role"] == "pm"

        observer.send_json({"type": "instruction.create", "text": "가격도 물어봐"})
        assert observer.receive_json()["type"] == "instruction.queued"

    assert len(client.get(f"/api/sessions/{session_id}/instructions").json()) == 1


def test_클라이언트는_참관만_되고_지시는_거부된다(client):
    session_id, study_id = _create_project_session(client)
    token = issue_client_project_token(study_id)

    with client.websocket_connect(f"/ws/observer/{session_id}?client_token={token}") as viewer:
        snapshot = viewer.receive_json()
        assert snapshot["type"] == "session.snapshot"
        # 참관(트랜스크립트 열람)은 정상적으로 열린다
        assert snapshot["viewer_role"] == "client"

        viewer.send_json({"type": "instruction.create", "text": "이건 들어가면 안 된다"})
        rejected = viewer.receive_json()

    assert rejected["type"] == "error"
    assert "PM만" in rejected["message"]
    # 큐에 아무것도 쌓이지 않아야 한다
    assert client.get(f"/api/sessions/{session_id}/instructions").json() == []


def test_다른_프로젝트_토큰으로는_백룸에_붙을_수_없다(client):
    session_id, _ = _create_project_session(client)
    other_token = issue_client_project_token("study_남의프로젝트")

    import pytest
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            f"/ws/observer/{session_id}?client_token={other_token}"
        ) as viewer:
            viewer.receive_json()
