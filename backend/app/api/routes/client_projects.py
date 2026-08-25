from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.schemas.project_report import ProjectAggregateReport
from app.schemas.session import SessionStatus
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
            status=session.status,
            duration_minutes=session.duration_minutes,
            created_at=session.created_at,
            started_at=session.started_at,
            ended_at=session.ended_at,
        )
        for session in sessions
    ]
