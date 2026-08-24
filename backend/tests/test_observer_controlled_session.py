def _create_session(client) -> str:
    response = client.post(
        "/api/sessions",
        json={
            "title": "Observer controlled interview",
            "duration_minutes": 20,
            "question_script": "1. Tell me about your experience.",
        },
    )
    assert response.status_code == 201
    return response.json()["session"]["id"]


def test_interviewee_waits_until_pm_starts_the_session(client):
    session_id = _create_session(client)

    with client.websocket_connect(f"/ws/interview/{session_id}") as interviewee:
        initial_state = interviewee.receive_json()
        assert initial_state["type"] == "session.state"
        assert initial_state["session"]["status"] == "created"

        start_response = client.post(f"/api/sessions/{session_id}/start")

        assert start_response.status_code == 200
        assert start_response.json()["status"] == "running"
        assert interviewee.receive_json()["session"]["status"] == "running"


def test_recording_upload_accepts_a_webm_file(client, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "azure_storage_connection_string", "")
    session_id = _create_session(client)

    response = client.post(
        f"/api/sessions/{session_id}/recording",
        files={"file": ("recording.webm", b"webm-recording", "video/webm")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "session_id": session_id,
        "video_recording_url": f"/recordings/{session_id}/recording.webm",
        "size_bytes": len(b"webm-recording"),
        "status": "uploaded",
    }


def test_ended_session_cannot_be_started_again(client):
    session_id = _create_session(client)
    assert client.post(f"/api/sessions/{session_id}/end").status_code == 200

    response = client.post(f"/api/sessions/{session_id}/start")

    assert response.status_code == 409
