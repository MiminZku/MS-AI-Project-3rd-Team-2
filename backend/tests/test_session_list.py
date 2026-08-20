"""세션 목록 조회 — 최근 생성순으로 내려오는지 확인."""


def _create(client, title: str) -> str:
    response = client.post(
        "/api/sessions",
        json={"title": title, "duration_minutes": 20, "question_script": ""},
    )
    assert response.status_code == 201
    return response.json()["session"]["id"]


def test_세션_목록은_최근_생성순으로_온다(client):
    first_id = _create(client, "첫 번째 세션")
    second_id = _create(client, "두 번째 세션")

    response = client.get("/api/sessions")
    assert response.status_code == 200

    body = response.json()
    ids = [item["id"] for item in body]
    assert ids.index(second_id) < ids.index(first_id)


def test_세션이_하나도_없으면_빈_목록이_온다(client):
    response = client.get("/api/sessions")
    assert response.status_code == 200
    assert response.json() == []
