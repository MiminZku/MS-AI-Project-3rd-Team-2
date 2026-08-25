"""PM-triggered project aggregate report regression tests."""


SCRIPT = "1. 현재 어떤 스마트폰을 사용하시나요?\n2. 선택한 이유는 무엇인가요?"


def _create_project(client) -> dict:
    response = client.post(
        "/api/projects",
        json={
            "title": "Galaxy vs iPhone 구매 의사결정 조사",
            "research_purpose": "스마트폰 선택 이유를 확인합니다.",
            "question_script": SCRIPT,
        },
    )
    assert response.status_code == 201
    return response.json()["study"]


def _create_completed_session(client, project_id: str, participant_id: str, answer: str, *, simulation: bool = False) -> str:
    created = client.post(
        "/api/sessions",
        json={"study_id": project_id, "title": participant_id, "duration_minutes": 20},
    )
    assert created.status_code == 201
    session_id = created.json()["session"]["id"]
    if simulation:
        from app.services.store import get_store
        import asyncio
        session = asyncio.run(get_store().get_session(session_id))
        session.is_simulation = True
        asyncio.run(get_store().save_session(session))

    with client.websocket_connect(f"/ws/interview/{session_id}") as interviewee:
        interviewee.receive_json()
        assert client.post(f"/api/sessions/{session_id}/start").status_code == 200
        interviewee.receive_json()
        interviewee.send_json({"type": "utterance", "text": answer})
        assert interviewee.receive_json()["type"] == "assistant.question"

    assert client.post(f"/api/sessions/{session_id}/end").status_code == 200
    return session_id


def test_end_only_completes_session_and_never_auto_generates_report(client):
    project = _create_project(client)
    session_id = _create_completed_session(client, project["id"], "INT-001", "아이폰이요.")

    session = client.get(f"/api/sessions/{session_id}").json()["session"]
    assert session["status"] == "ended"
    assert client.get(f"/api/sessions/{session_id}/report").status_code == 202
    aggregate = client.get(f"/api/projects/{project['id']}/aggregate-report")
    assert aggregate.status_code == 200
    assert aggregate.json()["status"] == "NOT_GENERATED"


def test_one_short_answer_can_generate_project_report_and_snapshot_can_refresh(client):
    project = _create_project(client)
    first = _create_completed_session(client, project["id"], "INT-001", "아이폰이요.")

    first_report = client.post(f"/api/projects/{project['id']}/aggregate-report")
    assert first_report.status_code == 200
    assert first_report.json()["status"] == "COMPLETED"
    assert first_report.json()["respondent_count"] == 1
    assert first_report.json()["included_session_ids"] == [first]
    assert "일반화하기 어렵습니다" in first_report.json()["content"]["data_sufficiency_notice"]

    second = _create_completed_session(client, project["id"], "INT-002", "카메라와 애플워치 연동 때문에 계속 아이폰을 사용합니다.")
    third = _create_completed_session(client, project["id"], "INT-003", "업무용 앱과 사진 품질이 좋아서 아이폰을 선택합니다.")
    unchanged = client.get(f"/api/projects/{project['id']}/aggregate-report").json()
    assert unchanged["respondent_count"] == 1
    assert {second, third}.isdisjoint(unchanged["included_session_ids"])

    refreshed = client.post(f"/api/projects/{project['id']}/aggregate-report")
    assert refreshed.status_code == 200
    assert refreshed.json()["respondent_count"] == 3
    assert set(refreshed.json()["included_session_ids"]) == {first, second, third}


def test_zero_completed_is_rejected_and_simulations_are_excluded(client):
    project = _create_project(client)
    zero = client.post(f"/api/projects/{project['id']}/aggregate-report")
    assert zero.status_code == 400
    assert zero.json()["detail"] == "완료된 인터뷰가 없어 리포트를 생성할 수 없습니다."

    _create_completed_session(client, project["id"], "SIM-001", "가상 응답입니다.", simulation=True)
    still_zero = client.post(f"/api/projects/{project['id']}/aggregate-report")
    assert still_zero.status_code == 400


def test_client_can_read_only_completed_project_report(client):
    project = _create_project(client)
    access = client.post("/api/client/projects/access", json={"access_id": project["access_id"]}).json()
    headers = {"X-Project-Access-Token": access["access_token"]}
    endpoint = f"/api/client/projects/{project['id']}/aggregate-report"
    assert client.get(endpoint, headers=headers).json() is None

    _create_completed_session(client, project["id"], "INT-001", "아이폰이요.")
    assert client.post(f"/api/projects/{project['id']}/aggregate-report").status_code == 200
    report = client.get(endpoint, headers=headers)
    assert report.status_code == 200
    assert report.json()["status"] == "COMPLETED"
