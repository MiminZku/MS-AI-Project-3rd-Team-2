from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Header, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.api.download_responses import (
    project_report_download_response,
    recording_download_response,
    transcript_download_response,
)
from app.schemas.project_report import ProjectAggregateReport
from app.schemas.session import SessionStatus, Turn
from app.services.client_project_access import (
    issue_client_project_token,
    verify_client_project_token,
)
from app.services.store import get_store


router = APIRouter(prefix="/client/projects", tags=["client-projects"])


class ClientProjectAccessRequest(BaseModel):
    access_id: str = Field(min_length=4, max_length=64)


class ClientProjectSummary(BaseModel):
    id: str
    title: str
    research_purpose: str
    created_at: datetime


class ClientSessionSummary(BaseModel):
    id: str
    # PM이 세션을 만들 때 입력한 익명 참가자 ID. 클라이언트가 "누구의 인터뷰인지"
    # 식별하는 유일한 값이므로 PM 대시보드에 보이는 것과 같은 값을 그대로 내려준다.
    title: str
    status: SessionStatus
    duration_minutes: int
    created_at: datetime
    started_at: datetime | None
    ended_at: datetime | None


class ClientProjectAccessResponse(BaseModel):
    project: ClientProjectSummary
    access_token: str


def _project_summary(study: object) -> ClientProjectSummary:
    return ClientProjectSummary(
        id=study.id,
        title=study.title,
        research_purpose=study.research_purpose,
        created_at=study.created_at,
    )


def _require_project_token(
    study_id: str,
    project_access_token: str | None,
) -> None:
    verify_client_project_token(project_access_token, study_id)


@router.post("/access", response_model=ClientProjectAccessResponse)
async def exchange_access_id(payload: ClientProjectAccessRequest) -> ClientProjectAccessResponse:
    access_id = payload.access_id.strip().upper()
    study = await get_store().get_study_by_access_id(access_id)
    if study is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "존재하지 않는 프로젝트 ID입니다.",
        )

    return ClientProjectAccessResponse(
        project=_project_summary(study),
        access_token=issue_client_project_token(study.id),
    )


@router.get("/{study_id}", response_model=ClientProjectSummary)
async def get_client_project(
    study_id: str,
    x_project_access_token: str | None = Header(default=None),
) -> ClientProjectSummary:
    _require_project_token(study_id, x_project_access_token)
    study = await get_store().get_study(study_id)
    if study is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "프로젝트를 찾을 수 없습니다.")
    return _project_summary(study)


@router.get("/{study_id}/aggregate-report", response_model=ProjectAggregateReport | None)
async def get_client_project_aggregate_report(
    study_id: str,
    x_project_access_token: str | None = Header(default=None),
) -> ProjectAggregateReport | None:
    _require_project_token(study_id, x_project_access_token)
    if await get_store().get_study(study_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "프로젝트를 찾을 수 없습니다.")
    report = await get_store().get_project_report(study_id)
    return report if report and report.status == "COMPLETED" else None


@router.get("/{study_id}/aggregate-report/download", response_class=Response)
async def download_client_project_report(
    study_id: str,
    format: str = Query("word", description="다운로드 파일 형식: word, powerbi, json"),
    x_project_access_token: str | None = Header(default=None),
) -> Response:
    _require_project_token(study_id, x_project_access_token)
    store = get_store()
    study = await store.get_study(study_id)
    if study is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "프로젝트를 찾을 수 없습니다.")

    return project_report_download_response(
        study,
        await store.get_project_report(study_id),
        format=format,
    )


async def _load_project_session(study_id: str, session_id: str):
    """토큰으로 접근한 프로젝트에 실제로 속한 세션인지 확인하고 돌려준다."""
    store = get_store()
    if await store.get_study(study_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "프로젝트를 찾을 수 없습니다.")

    session = await store.get_session(session_id)
    # 다른 프로젝트의 세션을 세션 ID만 갈아끼워 받아가지 못하게 소속을 검증한다.
    if session is None or session.study_id != study_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "인터뷰를 찾을 수 없습니다.")

    return session


@router.get("/{study_id}/sessions/{session_id}/transcript", response_model=list[Turn])
async def get_client_transcript(
    study_id: str,
    session_id: str,
    x_project_access_token: str | None = Header(default=None),
) -> list[Turn]:
    """채팅 형식 기록 열람용. 파일을 받지 않고 화면에서 바로 읽을 수 있게 한다."""
    _require_project_token(study_id, x_project_access_token)
    session = await _load_project_session(study_id, session_id)
    return await get_store().get_transcript(session.id)


@router.get("/{study_id}/sessions/{session_id}/transcript/download", response_class=Response)
async def download_client_transcript(
    study_id: str,
    session_id: str,
    x_project_access_token: str | None = Header(default=None),
) -> Response:
    _require_project_token(study_id, x_project_access_token)
    session = await _load_project_session(study_id, session_id)

    store = get_store()
    study = await store.get_study(study_id)
    return transcript_download_response(
        session,
        await store.get_transcript(session.id),
        project_title=study.title if study else None,
    )


@router.get("/{study_id}/sessions/{session_id}/recording/download", response_class=Response)
async def download_client_recording(
    study_id: str,
    session_id: str,
    x_project_access_token: str | None = Header(default=None),
) -> Response:
    _require_project_token(study_id, x_project_access_token)
    session = await _load_project_session(study_id, session_id)
    return await recording_download_response(session)


@router.get("/{study_id}/sessions", response_model=list[ClientSessionSummary])
async def get_client_project_sessions(
    study_id: str,
    x_project_access_token: str | None = Header(default=None),
) -> list[ClientSessionSummary]:
    _require_project_token(study_id, x_project_access_token)
    study = await get_store().get_study(study_id)
    if study is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "프로젝트를 찾을 수 없습니다.")

    sessions = await get_store().list_sessions(study_id)
    return [
        ClientSessionSummary(
            id=session.id,
            title=session.title,
            status=session.status,
            duration_minutes=session.duration_minutes,
            created_at=session.created_at,
            started_at=session.started_at,
            ended_at=session.ended_at,
        )
        for session in sessions
    ]
