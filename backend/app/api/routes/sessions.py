"""참관자(관리자)용 세션 API. 세션 생성 시 응답자용 인터뷰 링크를 발급한다."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import load_session, require_admin
from app.core.config import get_settings
from app.schemas.report import Report
from app.schemas.session import (
    Instruction,
    Session,
    SessionCreateRequest,
    SessionCreateResponse,
    Turn,
)
from app.services import orchestrator
from app.services.question_script import parse_question_script
from app.services.store import get_store

router = APIRouter(prefix="/sessions", tags=["sessions"], dependencies=[Depends(require_admin)])


def _interviewee_url(session_id: str) -> str:
    base = get_settings().interviewee_base_url.rstrip("/")
    return f"{base}/?session={session_id}"


@router.post("", response_model=SessionCreateResponse, status_code=201)
async def create_session(payload: SessionCreateRequest) -> SessionCreateResponse:
    session = Session(
        title=payload.title,
        duration_minutes=payload.duration_minutes,
        questions=parse_question_script(payload.question_script),
    )
    await get_store().save_session(session)
    return SessionCreateResponse(session=session, interviewee_url=_interviewee_url(session.id))


@router.get("/{session_id}", response_model=SessionCreateResponse)
async def get_session(session: Session = Depends(load_session)) -> SessionCreateResponse:
    return SessionCreateResponse(session=session, interviewee_url=_interviewee_url(session.id))


@router.get("/{session_id}/transcript", response_model=list[Turn])
async def get_transcript(session: Session = Depends(load_session)) -> list[Turn]:
    return await get_store().get_transcript(session.id)


@router.get("/{session_id}/instructions", response_model=list[Instruction])
async def get_instructions(session: Session = Depends(load_session)) -> list[Instruction]:
    return await get_store().list_instructions(session.id)


@router.post("/{session_id}/end", response_model=Session)
async def end_session(session: Session = Depends(load_session)) -> Session:
    return await orchestrator.end_session(session)


@router.get("/{session_id}/report", response_model=None)
async def get_report(session: Session = Depends(load_session)) -> Report | JSONResponse:
    report = await get_store().get_report(session.id)
    if report is None:
        # 세션 종료 직후엔 아직 생성 중일 수 있음. 대시보드는 이 상태면 폴링하거나
        # observer 소켓의 report.ready 이벤트를 기다리면 된다.
        return JSONResponse(status_code=202, content={"status": "pending"})
    return report
