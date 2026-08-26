"""다운로드 센터 백엔드: 인터뷰 기록 / 녹화 영상 / 프로젝트 리포트 파일."""


SCRIPT = "1. 요즘 어떤 AI 도구를 쓰시나요?"
DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _create_project(client) -> dict:
    response = client.post(
        "/api/projects",
        json={
            "title": "AI 코딩도구 사용성 조사",
            "research_purpose": "터미널 개발자 워크플로 파악",
            "question_script": SCRIPT,
        },
    )
    assert response.status_code == 201
    return response.json()["study"]


def _create_session(client, project_id: str, title: str = "P01-강민기") -> str:
    response = client.post(
        "/api/sessions",
        json={"study_id": project_id, "title": title, "duration_minutes": 20},
    )
    assert response.status_code == 201
    return response.json()["session"]["id"]


def _run_interview(client, session_id: str) -> None:
    with client.websocket_connect(f"/ws/interview/{session_id}") as interviewee:
        interviewee.receive_json()
        client.post(f"/api/sessions/{session_id}/start")
        interviewee.receive_json()
        for text in ["안녕하세요.", "클로드 씁니다.", "아니요, 더 없습니다."]:
            interviewee.send_json({"type": "utterance", "text": text})
            interviewee.receive_json()


def _client_token(client, access_id: str) -> str:
    response = client.post("/api/client/projects/access", json={"access_id": access_id})
    assert response.status_code == 200
    return response.json()["access_token"]


def _generate_report_and_wait(client, project_id: str, *, timeout: float = 10.0) -> dict:
    """리포트는 백그라운드에서 생성되므로 완료될 때까지 폴링한다."""
    import time

    assert client.post(f"/api/projects/{project_id}/aggregate-report").status_code == 200
    deadline = time.time() + timeout
    while time.time() < deadline:
        report = client.get(f"/api/projects/{project_id}/aggregate-report").json()
        if report["status"] in ("COMPLETED", "FAILED"):
            return report
        time.sleep(0.05)
    raise AssertionError("리포트 생성이 제한 시간 안에 끝나지 않았습니다.")


# =========================================================
# 인터뷰 기록
# =========================================================

def test_질문답변_기록_다운로드(client):
    project = _create_project(client)
    session_id = _create_session(client, project["id"])
    _run_interview(client, session_id)

    response = client.get(f"/api/sessions/{session_id}/transcript/download")

    assert response.status_code == 200
    assert response.headers["content-type"] == DOCX_TYPE
    assert len(response.content) > 0
    # 한글 참가자 ID가 파일명에 살아 있어야 한다
    assert "filename*=UTF-8''" in response.headers["content-disposition"]


def test_기록에_실제_대화가_담긴다(client):
    project = _create_project(client)
    session_id = _create_session(client, project["id"])
    _run_interview(client, session_id)

    from docx import Document
    import io

    response = client.get(f"/api/sessions/{session_id}/transcript/download")
    document = Document(io.BytesIO(response.content))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)

    assert "P01-강민기" in text
    assert "클로드 씁니다." in text
    assert "요즘 어떤 AI 도구를 쓰시나요?" in text


# =========================================================
# 녹화 영상
# =========================================================

def test_녹화본이_없으면_404(client):
    project = _create_project(client)
    session_id = _create_session(client, project["id"])

    response = client.get(f"/api/sessions/{session_id}/recording/download")

    assert response.status_code == 404


def test_업로드된_녹화본을_받는다(client, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "azure_storage_connection_string", "")
    project = _create_project(client)
    session_id = _create_session(client, project["id"])

    client.post(
        f"/api/sessions/{session_id}/recording",
        files={"file": ("recording.webm", b"FAKE-WEBM-BYTES", "video/webm")},
    )

    response = client.get(f"/api/sessions/{session_id}/recording/download")

    assert response.status_code == 200
    assert response.headers["content-type"] == "video/webm"
    assert response.content == b"FAKE-WEBM-BYTES"


# =========================================================
# 프로젝트 리포트
# =========================================================

def test_리포트_생성_전에는_다운로드가_404(client):
    project = _create_project(client)

    response = client.get(f"/api/projects/{project['id']}/aggregate-report/download")

    assert response.status_code == 404
    assert "생성" in response.json()["detail"]


def test_리포트를_생성하면_문서로_받을_수_있다(client):
    project = _create_project(client)
    session_id = _create_session(client, project["id"])
    _run_interview(client, session_id)

    assert _generate_report_and_wait(client, project["id"])["status"] == "COMPLETED"

    response = client.get(f"/api/projects/{project['id']}/aggregate-report/download")

    assert response.status_code == 200
    assert response.headers["content-type"] == DOCX_TYPE
    assert len(response.content) > 0


def test_완료된_인터뷰가_없으면_리포트_생성이_거부된다(client):
    project = _create_project(client)

    response = client.post(f"/api/projects/{project['id']}/aggregate-report")

    assert response.status_code == 400


# =========================================================
# 클라이언트 경로 (Project Access 토큰)
# =========================================================

def test_클라이언트도_같은_자료를_받는다(client):
    project = _create_project(client)
    session_id = _create_session(client, project["id"])
    _run_interview(client, session_id)
    _generate_report_and_wait(client, project["id"])

    token = _client_token(client, project["access_id"])
    headers = {"X-Project-Access-Token": token}

    transcript = client.get(
        f"/api/client/projects/{project['id']}/sessions/{session_id}/transcript/download",
        headers=headers,
    )
    report = client.get(
        f"/api/client/projects/{project['id']}/aggregate-report/download",
        headers=headers,
    )

    assert transcript.status_code == 200
    assert report.status_code == 200


def test_토큰_없이는_클라이언트_다운로드가_막힌다(client):
    project = _create_project(client)
    session_id = _create_session(client, project["id"])

    response = client.get(
        f"/api/client/projects/{project['id']}/sessions/{session_id}/transcript/download"
    )

    assert response.status_code == 401


def test_다른_프로젝트의_인터뷰는_받을_수_없다(client):
    """세션 ID만 갈아끼워 남의 프로젝트 자료를 받아가지 못해야 한다."""
    mine = _create_project(client)
    other = client.post(
        "/api/projects",
        json={
            "title": "다른 프로젝트",
            "research_purpose": "무관",
            "question_script": SCRIPT,
        },
    ).json()["study"]
    other_session = _create_session(client, other["id"], title="P99")

    token = _client_token(client, mine["access_id"])

    response = client.get(
        f"/api/client/projects/{mine['id']}/sessions/{other_session}/transcript/download",
        headers={"X-Project-Access-Token": token},
    )

    assert response.status_code == 404


# =========================================================
# 클라이언트 세션 목록 식별자
# =========================================================

def test_클라이언트_세션_목록에_참가자_ID가_나온다(client):
    """PM이 입력한 세션 제목이 그대로 보여야 누구의 인터뷰인지 식별된다."""
    project = _create_project(client)
    _create_session(client, project["id"], title="P07-김민수")

    token = _client_token(client, project["access_id"])
    sessions = client.get(
        f"/api/client/projects/{project['id']}/sessions",
        headers={"X-Project-Access-Token": token},
    ).json()

    assert [session["title"] for session in sessions] == ["P07-김민수"]


def test_클라이언트가_기록을_채팅용으로_조회한다(client):
    """파일을 받지 않고 화면에서 바로 읽는 경로."""
    project = _create_project(client)
    session_id = _create_session(client, project["id"])
    _run_interview(client, session_id)

    token = _client_token(client, project["access_id"])
    turns = client.get(
        f"/api/client/projects/{project['id']}/sessions/{session_id}/transcript",
        headers={"X-Project-Access-Token": token},
    ).json()

    speakers = [turn["speaker"] for turn in turns]
    assert "assistant" in speakers and "interviewee" in speakers
    assert any("클로드 씁니다." == turn["text"] for turn in turns)


def test_다른_프로젝트의_기록은_조회할_수_없다(client):
    mine = _create_project(client)
    other = client.post(
        "/api/projects",
        json={"title": "다른 프로젝트", "research_purpose": "무관", "question_script": SCRIPT},
    ).json()["study"]
    other_session = _create_session(client, other["id"], title="P99")

    token = _client_token(client, mine["access_id"])
    response = client.get(
        f"/api/client/projects/{mine['id']}/sessions/{other_session}/transcript",
        headers={"X-Project-Access-Token": token},
    )

    assert response.status_code == 404


def test_문서에_한글_글꼴이_지정된다(client):
    """Word에서 한글이 깨지지 않으려면 run마다 eastAsia 글꼴이 있어야 한다."""
    import io
    import zipfile

    project = _create_project(client)
    session_id = _create_session(client, project["id"])
    _run_interview(client, session_id)

    response = client.get(f"/api/sessions/{session_id}/transcript/download")
    document_xml = zipfile.ZipFile(io.BytesIO(response.content)).read("word/document.xml").decode("utf-8")

    assert "w:eastAsia" in document_xml
    assert "맑은 고딕" in document_xml
    assert "P01-강민기" in document_xml
