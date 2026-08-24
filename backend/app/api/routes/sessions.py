from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
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
from app.services.connections import manager
from app.services.question_script import parse_question_script
from app.services.recordings import RecordingUploadResponse, save_recording
from app.services.store import get_store
from app.schemas.messages import server_message


router = APIRouter(
    prefix="/sessions",
    tags=["sessions"],
    dependencies=[Depends(require_admin)],
)


# =========================================================
# Interviewee URL
# =========================================================

def _interviewee_url(
    session_id: str,
) -> str:

    base = (
        get_settings()
        .interviewee_base_url
        .rstrip("/")
    )

    return f"{base}/?session={session_id}"


# =========================================================
# Session 생성
# =========================================================

@router.post(
    "",
    response_model=SessionCreateResponse,
    status_code=201,
)
async def create_session(
    payload: SessionCreateRequest,
) -> SessionCreateResponse:

    store = get_store()

    # -----------------------------------------------------
    # 1. ResearchStudy 기반 Session 생성
    # -----------------------------------------------------

    if payload.study_id:

        study = await store.get_study(
            payload.study_id
        )

        if study is None:
            raise HTTPException(
                status_code=404,
                detail="ResearchStudy를 찾을 수 없습니다.",
            )

        session = Session(
            study_id=study.id,

            # Study와 연결된 Session은
            # 기본적으로 Study 제목을 사용
            title=study.title,

            duration_minutes=(
                payload.duration_minutes
            ),

            # ⭐ 중요
            # 질문지를 다시 파싱하지 않고
            # Study에서 확정된 질문을 그대로 사용
            questions=study.questions,
        )

    # -----------------------------------------------------
    # 2. 기존 Session 생성 방식
    # -----------------------------------------------------

    else:

        questions = parse_question_script(
            payload.question_script
        )

        session = Session(
            study_id=None,
            title=payload.title,
            duration_minutes=(
                payload.duration_minutes
            ),
            questions=questions,
        )

    # -----------------------------------------------------
    # 3. Session 저장
    # -----------------------------------------------------

    await store.save_session(
        session
    )

    # -----------------------------------------------------
    # 4. Interview URL 반환
    # -----------------------------------------------------

    return SessionCreateResponse(
        session=session,
        interviewee_url=(
            _interviewee_url(
                session.id
            )
        ),
    )


# =========================================================
# Session 조회
# =========================================================

@router.get(
    "/{session_id}",
    response_model=SessionCreateResponse,
)
async def get_session(
    session: Session = Depends(load_session),
) -> SessionCreateResponse:

    return SessionCreateResponse(
        session=session,
        interviewee_url=(
            _interviewee_url(
                session.id
            )
        ),
    )


# =========================================================
# Transcript 조회
# =========================================================

@router.get(
    "/{session_id}/transcript",
    response_model=list[Turn],
)
async def get_transcript(
    session: Session = Depends(load_session),
) -> list[Turn]:

    return await get_store().get_transcript(
        session.id
    )


# =========================================================
# Observer Instructions 조회
# =========================================================

@router.get(
    "/{session_id}/instructions",
    response_model=list[Instruction],
)
async def get_instructions(
    session: Session = Depends(load_session),
) -> list[Instruction]:

    return await get_store().list_instructions(
        session.id
    )


# =========================================================
# Session 종료
# =========================================================

@router.post(
    "/{session_id}/start",
    response_model=Session,
)
async def start_session(
    session: Session = Depends(load_session),
) -> Session:
    if session.status == "ended":
        raise HTTPException(status_code=409, detail="Cannot start an ended session.")
    if session.status == "running":
        return session

    started = await orchestrator.start_session_if_needed(session)
    await manager.broadcast_to_observers(
        started.id,
        server_message("session.started", session=started.model_dump(mode="json")),
    )
    await manager.send_to_interviewee(
        started.id,
        server_message(
            "session.state",
            session={"id": started.id, "title": started.title, "status": started.status},
        ),
    )
    return started


@router.post(
    "/{session_id}/recording",
    response_model=RecordingUploadResponse,
)
async def upload_recording(
    file: UploadFile = File(...),
    session: Session = Depends(load_session),
) -> RecordingUploadResponse:
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(status_code=422, detail="Recording must be a video file.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Recording file is empty.")

    return await save_recording(session.id, content)


@router.post(
    "/{session_id}/end",
    response_model=Session,
)
async def end_session(
    session: Session = Depends(load_session),
) -> Session:

    return await orchestrator.end_session(
        session
    )


# =========================================================
# Report 조회
# =========================================================

@router.get(
    "/{session_id}/report",
    response_model=None,
)
async def get_report(
    session: Session = Depends(load_session),
) -> Report | JSONResponse:

    report = await get_store().get_report(
        session.id
    )

    if report is None:

        # 인터뷰 종료 직후에는
        # 비동기로 Report가 생성 중일 수 있음.
        return JSONResponse(
            status_code=202,
            content={
                "status": "pending"
            },
        )

    return report
