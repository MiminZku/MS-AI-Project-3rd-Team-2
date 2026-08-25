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


def _create_project(client, title: str) -> dict:
    response = client.post(
        "/api/projects",
        json={
            "title": title,
            "research_purpose": f"{title} purpose",
            "question_script": "1. What would influence your purchase decision?",
        },
    )
    assert response.status_code == 201
    return response.json()["study"]


class _FailingSlotGenerator:
    async def generate(self, **_: object) -> list[object]:
        raise RuntimeError("Azure OpenAI unavailable")


def test_project_creation_survives_information_slot_generation_failure(client, monkeypatch):
    from app.api.routes import studies

    monkeypatch.setattr(studies, "get_slot_generator", lambda: _FailingSlotGenerator())

    response = client.post(
        "/api/projects",
        json={
            "title": "Fallback project",
            "research_purpose": "Verify resilient local project creation",
            "question_script": "1. What matters most to you?",
        },
    )

    assert response.status_code == 201
    assert response.json()["study"]["information_slots"] == []


def test_project_creation_survives_information_slot_generator_initialization_failure(
    client, monkeypatch
):
    from app.api.routes import studies

    def raise_initialization_error():
        raise RuntimeError("Azure OpenAI configuration unavailable")

    monkeypatch.setattr(studies, "get_slot_generator", raise_initialization_error)

    response = client.post(
        "/api/projects",
        json={
            "title": "Initialization fallback project",
            "research_purpose": "Verify resilient local project creation",
            "question_script": "1. What matters most to you?",
        },
    )

    assert response.status_code == 201
    assert response.json()["study"]["information_slots"] == []


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


def test_respondent_state_uses_project_title_without_replacing_participant_id(client):
    project_title = "Galaxy vs iPhone 구매 의사결정 조사"
    project = _create_project(client, project_title)
    created = client.post(
        "/api/sessions",
        json={
            "study_id": project["id"],
            "title": "USER-001",
            "duration_minutes": 60,
            "question_script": "",
        },
    )
    assert created.status_code == 201
    session_id = created.json()["session"]["id"]

    with client.websocket_connect(f"/ws/interview/{session_id}") as respondent:
        initial = respondent.receive_json()["session"]
        assert initial["title"] == "USER-001"
        assert initial["project_title"] == project_title

        started = client.post(f"/api/sessions/{session_id}/start")
        assert started.status_code == 200
        running = respondent.receive_json()["session"]
        assert running["title"] == "USER-001"
        assert running["project_title"] == project_title


def test_respondent_state_uses_the_current_sessions_linked_project_title(client):
    first_project = _create_project(client, "First project title")
    second_project = _create_project(client, "Second project title")

    first_session = client.post(
        "/api/sessions",
        json={
            "study_id": first_project["id"],
            "title": "USER-001",
            "duration_minutes": 60,
            "question_script": "",
        },
    )
    second_session = client.post(
        "/api/sessions",
        json={
            "study_id": second_project["id"],
            "title": "USER-002",
            "duration_minutes": 60,
            "question_script": "",
        },
    )
    assert first_session.status_code == 201
    assert second_session.status_code == 201

    with client.websocket_connect(
        f"/ws/interview/{first_session.json()['session']['id']}"
    ) as first_respondent:
        assert first_respondent.receive_json()["session"]["project_title"] == "First project title"

    with client.websocket_connect(
        f"/ws/interview/{second_session.json()['session']['id']}"
    ) as second_respondent:
        assert second_respondent.receive_json()["session"]["project_title"] == "Second project title"


def test_respondent_state_does_not_fallback_to_participant_id_when_study_is_missing(client):
    session_id = _create_session(client)

    with client.websocket_connect(f"/ws/interview/{session_id}") as respondent:
        state = respondent.receive_json()["session"]
        assert state["title"] == "Observer controlled interview"
        assert state["project_title"] is None


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
