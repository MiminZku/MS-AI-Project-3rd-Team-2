import re


def _create_project(client, title: str) -> dict:
    response = client.post(
        "/api/projects",
        json={
            "title": title,
            "research_purpose": f"{title} purpose",
            "question_script": "1. 이 서비스에서 가장 중요하게 생각하는 점은 무엇인가요?",
        },
    )
    assert response.status_code == 201
    return response.json()["study"]


def test_pm_project_creation_returns_a_unique_access_id(client):
    first = _create_project(client, "Laptop study")
    second = _create_project(client, "Mobile study")

    assert re.fullmatch(r"PRJ-[A-Z0-9]{12}", first["access_id"])
    assert re.fullmatch(r"PRJ-[A-Z0-9]{12}", second["access_id"])
    assert first["access_id"] != second["access_id"]


def test_existing_projects_are_backfilled_with_access_ids(client):
    response = client.get("/api/projects")

    assert response.status_code == 200
    assert response.json()
    assert all(project["access_id"] for project in response.json())


def test_client_access_id_grants_only_its_project(client):
    first = _create_project(client, "First study")
    second = _create_project(client, "Second study")

    grant = client.post(
        "/api/client/projects/access",
        json={"access_id": first["access_id"]},
    )
    assert grant.status_code == 200
    token = grant.json()["access_token"]
    headers = {"X-Project-Access-Token": token}

    allowed = client.get(f"/api/client/projects/{first['id']}", headers=headers)
    assert allowed.status_code == 200
    assert allowed.json()["id"] == first["id"]
    assert "question_script" not in allowed.json()

    blocked = client.get(f"/api/client/projects/{second['id']}", headers=headers)
    assert blocked.status_code == 403


def test_unknown_access_id_has_a_client_safe_error(client):
    response = client.post(
        "/api/client/projects/access",
        json={"access_id": "PRJ-DOESNOTEXIST"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "존재하지 않는 프로젝트 ID입니다."


def test_pm_session_keeps_the_anonymous_participant_id(client):
    study = _create_project(client, "Anonymous participant study")

    response = client.post(
        "/api/sessions",
        json={
            "study_id": study["id"],
            "title": "INT-001",
            "duration_minutes": 60,
            "question_script": "",
        },
    )

    assert response.status_code == 201
    assert response.json()["session"]["title"] == "INT-001"
