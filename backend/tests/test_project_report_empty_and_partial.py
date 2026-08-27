"""실측 회귀 2건.

A) "터미널 기반 AI 코딩 환경..." 프로젝트 (완료 19건)
   -> 8 validation errors for StudyReportAnalysis: themes/key_drivers/... Field required
   원인: chat.completions 폴백이 json_object 모드라 스키마를 강제하지 않아,
        모델이 앞쪽 섹션만 만든 "유효한" JSON을 반환했다.
   대응: 폴백 사다리에 json_schema(strict) 단계 추가 (test_structured_call.py 참고)
        + 스키마가 strict 강제 가능한 형태인지 여기서 확인한다.

B) "삼성 노트북 vs LG gram..." 프로젝트 (완료 3건)
   -> 응답자 발화가 없어 리포트를 생성할 수 없습니다
   확인: 배포 데이터를 직접 조회한 결과 3건 모두 전사 턴이 0개였다.
        코드 버그가 아니라 인터뷰가 실제로 진행되지 않은 데이터 문제.
   대응: 어느 인터뷰가 비어 있는지 메시지에 밝혀 원인을 즉시 판단하게 한다.

주의: Azure 자격 증명을 넣으면 인터뷰 WS가 실제 Azure를 호출해 멈춘다.
      그래서 설정은 건드리지 않고 project_report 모듈 경계만 바꿔 끼운다.
"""

import time

import pytest

from app.schemas.study_report import StudyReportAnalysis
from app.services import project_report as project_report_module

SCRIPT = "1. 요즘 어떤 AI 도구를 쓰시나요?"


class _FakeSettings:
    """Azure 분석 경로를 타게 하되 실제 호출은 하지 않는다."""

    use_azure_openai = True


def _force_azure_branch(monkeypatch) -> None:
    monkeypatch.setattr(project_report_module, "get_settings", lambda: _FakeSettings())


def _create_project(client, title: str) -> dict:
    response = client.post(
        "/api/projects",
        json={"title": title, "research_purpose": "목적", "question_script": SCRIPT},
    )
    assert response.status_code == 201
    return response.json()["study"]


def _ended_session_without_utterances(client, project_id: str, title: str) -> str:
    """인터뷰를 진행하지 않고 종료한 세션 (전사 0턴)."""
    session_id = client.post(
        "/api/sessions",
        json={"study_id": project_id, "title": title, "duration_minutes": 20},
    ).json()["session"]["id"]
    assert client.post(f"/api/sessions/{session_id}/end").status_code == 200
    return session_id


def _ended_session_with_utterances(client, project_id: str, title: str, answer: str) -> str:
    session_id = client.post(
        "/api/sessions",
        json={"study_id": project_id, "title": title, "duration_minutes": 20},
    ).json()["session"]["id"]
    with client.websocket_connect(f"/ws/interview/{session_id}") as interviewee:
        interviewee.receive_json()
        client.post(f"/api/sessions/{session_id}/start")
        interviewee.receive_json()
        interviewee.send_json({"type": "utterance", "text": answer})
        interviewee.receive_json()
    client.post(f"/api/sessions/{session_id}/end")
    return session_id


def _generate_and_wait(client, project_id: str, *, timeout: float = 10.0) -> dict:
    assert client.post(f"/api/projects/{project_id}/aggregate-report").status_code == 200
    deadline = time.time() + timeout
    while time.time() < deadline:
        report = client.get(f"/api/projects/{project_id}/aggregate-report").json()
        if report["status"] in ("COMPLETED", "FAILED"):
            return report
        time.sleep(0.05)
    raise AssertionError("리포트 생성이 제한 시간 안에 끝나지 않았습니다.")


def _fixture_analysis() -> StudyReportAnalysis:
    import json
    from pathlib import Path

    fixture = (
        Path(__file__).resolve().parents[1]
        / "app" / "ai-interview-report" / "study_report.json"
    )
    return StudyReportAnalysis.model_validate(json.loads(fixture.read_text(encoding="utf-8")))


# =========================================================
# B) 전사가 비어 있는 경우
# =========================================================

def test_전사가_모두_비면_어느_인터뷰인지_알려준다(client, monkeypatch):
    """'응답자 발화가 없다'만으로는 버그인지 데이터 문제인지 알 수 없다."""
    _force_azure_branch(monkeypatch)

    project = _create_project(client, "삼성 노트북 vs LG gram 구매·사용 경험 인터뷰")
    for title in ("123123", "P02", "P03"):
        _ended_session_without_utterances(client, project["id"], title)

    report = _generate_and_wait(client, project["id"])

    assert report["status"] == "FAILED"
    message = report["error_message"]
    assert "완료된 인터뷰 3건 모두" in message
    for title in ("123123", "P02", "P03"):
        assert title in message
    assert "인터뷰가 실제로 진행되었는지" in message


def test_발화_없는_인터뷰만_제외하고_나머지로_생성한다(client, monkeypatch):
    _force_azure_branch(monkeypatch)

    project = _create_project(client, "일부 공백 프로젝트")
    _ended_session_with_utterances(client, project["id"], "P01", "클로드를 씁니다.")
    _ended_session_without_utterances(client, project["id"], "EMPTY-01")
    _ended_session_with_utterances(client, project["id"], "P02", "코덱스를 씁니다.")

    seen: dict = {}

    class _FakeAnalyzer:
        async def analyze(self, study, participant_reports):
            seen["participant_ids"] = [r["participant_id"] for r in participant_reports]
            return _fixture_analysis()

    monkeypatch.setattr(
        project_report_module, "get_study_report_analyzer", lambda: _FakeAnalyzer()
    )

    report = _generate_and_wait(client, project["id"])

    assert report["status"] == "COMPLETED", report.get("error_message")
    # 발화 없는 세션은 분석 입력에서 빠진다 (목록 순서는 최신순이라 무관)
    assert set(seen["participant_ids"]) == {"P01", "P02"}
    assert "EMPTY-01" not in seen["participant_ids"]
    # 집계 수치도 실제 분석된 건수와 일치해야 한다
    assert report["respondent_count"] == 2
    assert len(report["included_session_ids"]) == 2
    assert "1건을 제외하고 분석했습니다" in report["content"]["data_sufficiency_notice"]


# =========================================================
# A) 스키마 강제 가능 여부
# =========================================================

def test_종합_리포트_스키마는_strict_강제가_가능하다():
    """json_schema(strict) 로 서버가 강제할 수 있어야 필드 누락이 원천 차단된다."""
    schema = StudyReportAnalysis.model_json_schema()
    problems: list[str] = []

    def walk(node, path="root"):
        if isinstance(node, dict):
            if node.get("type") == "object":
                props = set((node.get("properties") or {}).keys())
                required = set(node.get("required") or [])
                if props - required:
                    problems.append(f"{path}: required 누락 {sorted(props - required)}")
                if node.get("additionalProperties") is not False:
                    problems.append(f"{path}: additionalProperties != false")
            for key, value in node.items():
                if key in ("properties", "$defs"):
                    for name, sub in value.items():
                        walk(sub, f"{path}.{name}")
                elif isinstance(value, (dict, list)):
                    walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{path}[{index}]")

    walk(schema)

    assert problems == [], f"strict 모드로 강제할 수 없는 지점: {problems[:5]}"


def test_스키마에_선택_필드를_추가하면_안_된다():
    """실측 회귀: data_sufficiency_notice 를 기본값 있는 선택 필드로 추가했더니
    리포트 생성이 통째로 실패했다.

    pydantic은 기본값이 있는 필드를 required에서 뺀다. 그러면 Azure Structured
    Outputs(strict)가 "모든 속성은 required여야 한다"며 요청을 400으로 거부하고,
    그 400은 폴백 로직상 "json_schema 미지원"으로 해석돼 스키마를 강제하지 않는
    json_object 모드로 내려간다. 결국 모델이 섹션 일부만 만든 응답을 내놓아
    "8 validation errors ... Field required"가 났다.

    새 필드가 필요하면 기본값 없이(required) 추가하고, 값이 없을 수 있으면
    타입을 `X | None` 으로 두어 모델이 null 을 채우게 해야 한다.
    """
    schema = StudyReportAnalysis.model_json_schema()

    properties = set(schema["properties"].keys())
    required = set(schema.get("required", []))

    assert properties - required == set(), (
        "다음 필드가 required 에서 빠져 strict 강제가 깨집니다: "
        f"{sorted(properties - required)}"
    )


def test_생성된_리포트_샘플이_스키마를_만족한다():
    """테스트들이 기대는 전제(고정 샘플이 유효하다)가 깨지면 바로 알 수 있게 한다."""
    import json
    from pathlib import Path

    fixture = (
        Path(__file__).resolve().parents[1]
        / "app" / "ai-interview-report" / "study_report.json"
    )

    assert StudyReportAnalysis.model_validate(
        json.loads(fixture.read_text(encoding="utf-8"))
    )


@pytest.mark.parametrize(
    "missing_field",
    ["themes", "key_drivers", "pain_points", "needs", "evidence"],
)
def test_섹션이_빠진_응답은_검증에서_걸린다(missing_field: str):
    """실측 오류(Field required)가 실제로 재현되는지 확인한다."""
    import json
    from pathlib import Path

    fixture = (
        Path(__file__).resolve().parents[1]
        / "app" / "ai-interview-report" / "study_report.json"
    )
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    payload.pop(missing_field)

    with pytest.raises(ValueError, match=missing_field):
        StudyReportAnalysis.model_validate(payload)
