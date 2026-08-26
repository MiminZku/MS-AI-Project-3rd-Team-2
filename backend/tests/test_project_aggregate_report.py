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


def _generate_and_wait(client, project_id: str, *, timeout: float = 10.0) -> dict:
    """리포트 생성을 시작하고 완료될 때까지 폴링한다.

    생성은 백그라운드에서 돌기 때문에 POST는 GENERATING만 돌려준다.
    (응답자가 많으면 분석에 수 분이 걸려 HTTP 요청 안에서 끝낼 수 없다.)
    """
    import time

    started = client.post(f"/api/projects/{project_id}/aggregate-report")
    assert started.status_code == 200, started.text
    assert started.json()["status"] in ("GENERATING", "COMPLETED")

    deadline = time.time() + timeout
    while time.time() < deadline:
        report = client.get(f"/api/projects/{project_id}/aggregate-report").json()
        if report["status"] in ("COMPLETED", "FAILED"):
            return report
        time.sleep(0.05)

    raise AssertionError("리포트 생성이 제한 시간 안에 끝나지 않았습니다.")


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

    first_report = _generate_and_wait(client, project["id"])
    assert first_report["status"] == "COMPLETED"
    assert first_report["respondent_count"] == 1
    assert first_report["included_session_ids"] == [first]
    assert "일반화하기 어렵습니다" in first_report["content"]["data_sufficiency_notice"]

    second = _create_completed_session(client, project["id"], "INT-002", "카메라와 애플워치 연동 때문에 계속 아이폰을 사용합니다.")
    third = _create_completed_session(client, project["id"], "INT-003", "업무용 앱과 사진 품질이 좋아서 아이폰을 선택합니다.")
    unchanged = client.get(f"/api/projects/{project['id']}/aggregate-report").json()
    assert unchanged["respondent_count"] == 1
    assert {second, third}.isdisjoint(unchanged["included_session_ids"])

    refreshed = _generate_and_wait(client, project["id"])
    assert refreshed["status"] == "COMPLETED"
    assert refreshed["respondent_count"] == 3
    assert set(refreshed["included_session_ids"]) == {first, second, third}


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
    assert _generate_and_wait(client, project["id"])["status"] == "COMPLETED"
    report = client.get(endpoint, headers=headers)
    assert report.status_code == 200
    assert report.json()["status"] == "COMPLETED"


# =========================================================
# 생성이 중간에 끊긴 경우 (실측 회귀)
# =========================================================

def test_생성_중_상태로_멈춰있으면_오래된_경우_다시_시작한다(client):
    """요청이 끊겨 GENERATING으로 박히면 그 프로젝트는 영영 리포트를 못 만들었다."""
    import asyncio
    from datetime import timedelta

    from app.schemas.project_report import ProjectAggregateReport
    from app.schemas.session import utcnow
    from app.services.store import get_store

    project = _create_project(client)
    _create_completed_session(client, project["id"], "INT-001", "아이폰이요.")

    # 앞선 실행이 죽어 GENERATING 그대로 남은 상황을 재현한다
    stuck = ProjectAggregateReport(
        project_id=project["id"],
        status="GENERATING",
        updated_at=utcnow() - timedelta(hours=2),
    )
    asyncio.run(get_store().save_project_report(stuck))

    report = _generate_and_wait(client, project["id"])

    assert report["status"] == "COMPLETED"
    assert report["respondent_count"] == 1


def test_방금_시작한_생성은_중복_실행하지_않는다(client):
    """짧은 간격의 재클릭이 같은 분석을 두 번 돌리면 안 된다."""
    import asyncio

    from app.schemas.project_report import ProjectAggregateReport
    from app.schemas.session import utcnow
    from app.services.store import get_store

    project = _create_project(client)
    _create_completed_session(client, project["id"], "INT-001", "아이폰이요.")

    in_flight = ProjectAggregateReport(
        project_id=project["id"],
        status="GENERATING",
        respondent_count=99,
        updated_at=utcnow(),
    )
    asyncio.run(get_store().save_project_report(in_flight))

    response = client.post(f"/api/projects/{project['id']}/aggregate-report")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "GENERATING"
    # 진행 중인 스냅샷을 그대로 돌려줬는지 (새로 시작하지 않았는지) 확인
    assert body["respondent_count"] == 99
