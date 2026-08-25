from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
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

            # PM이 제공한 익명 참가자 ID를 세션 식별자로 유지한다.
            # 기존 호출 호환성을 위해 값이 비어 있을 때만 프로젝트 제목으로 보완한다.
            title=payload.title.strip() or study.title,

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
# Session 목록 조회 (전체 세션 목록)
# =========================================================

@router.get(
    "",
    response_model=list[Session],
)
async def list_sessions() -> list[Session]:

    return await get_store().list_sessions()


# =========================================================
# Session 삭제
# =========================================================

@router.delete(
    "/{session_id}",
    status_code=204,
)
async def delete_session(
    session_id: str,
) -> None:

    store = get_store()

    session = await store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail="세션을 찾을 수 없습니다.",
        )

    await store.delete_session(session_id)


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

    started = await orchestrator.start_session_if_needed(
        session,
        broadcast_observer_state=False,
    )
    await manager.broadcast_to_observers(
        started.id,
        server_message("session.started", session=started.model_dump(mode="json")),
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

    result = await save_recording(session.id, content)

    # 저장된 녹화본 URL을 세션에도 반영해야 종료 후 리포트/대시보드에서 다시 찾을 수 있다.
    session.video_recording_url = result.video_recording_url
    await get_store().save_session(session)

    return result


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


# NOTE: 과거 이 위치에 POST /{session_id}/recording 핸들러가 중복 정의되어 있었다.
# FastAPI 는 먼저 등록된 라우트를 사용하므로 이 두 번째 정의는 한 번도 실행되지 않는 죽은 코드였고
# (openapi 생성 시 Duplicate Operation ID 경고 발생), 녹화본 URL 이 세션에 저장되지 않는 원인이었다.
# 실제 동작하던 위쪽 핸들러(save_recording 사용)에 세션 저장 로직을 합치고 이 중복 정의는 제거했다.
