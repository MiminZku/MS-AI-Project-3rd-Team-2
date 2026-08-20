from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import require_admin
from app.schemas.study import (
    ResearchStudy,
    ResearchStudyCreateRequest,
    ResearchStudyCreateResponse,
)
from app.services.question_script import parse_question_script
from app.services.report.slot_generator import get_slot_generator
from app.services.store import get_store


router = APIRouter(
    prefix="/projects",
    tags=["projects"],
    dependencies=[
        Depends(require_admin)
    ],
)


# =========================================================
# Research Study 생성
# =========================================================

@router.post(
    "",
    response_model=ResearchStudyCreateResponse,
    status_code=201,
)
async def create_study(
    payload: ResearchStudyCreateRequest,
) -> ResearchStudyCreateResponse:

    # 1. 질문지 파싱
    questions = parse_question_script(
        payload.question_script
    )

    if not questions:
        raise HTTPException(
            status_code=400,
            detail="질문지에서 질문을 찾을 수 없습니다.",
        )

    # 2. GPT-5.1로 Information Slot 자동 생성
    slot_generator = get_slot_generator()

    information_slots = await slot_generator.generate(
        title=payload.title,
        research_purpose=payload.research_purpose,
        question_script=payload.question_script,
        questions=questions,
    )

    # 3. ResearchStudy 생성
    study = ResearchStudy(
        title=payload.title,
        research_purpose=payload.research_purpose,
        question_script=payload.question_script,
        questions=questions,
        information_slots=information_slots,
    )

    # 4. 저장
    await get_store().save_study(
        study
    )

    # 5. 반환
    return ResearchStudyCreateResponse(
        study=study
    )


# =========================================================
# Research Study 목록 조회 (전체 프로젝트 목록)
# =========================================================

@router.get(
    "",
    response_model=list[ResearchStudy],
)
async def list_studies() -> list[ResearchStudy]:

    return await get_store().list_studies()


# =========================================================
# Research Study 조회
# =========================================================

@router.get(
    "/{study_id}",
    response_model=ResearchStudyCreateResponse,
)
async def get_study(
    study_id: str,
) -> ResearchStudyCreateResponse:

    study = await get_store().get_study(
        study_id
    )

    if study is None:
        raise HTTPException(
            status_code=404,
            detail="ResearchStudy를 찾을 수 없습니다.",
        )

    return ResearchStudyCreateResponse(
        study=study
    )


# =========================================================
# Research Study 산하 Sessions 목록 조회
# =========================================================

@router.get(
    "/{study_id}/sessions",
    response_model=list[Session],
)
async def list_study_sessions(
    study_id: str,
) -> list[Session]:

    study = await get_store().get_study(study_id)
    if study is None:
        raise HTTPException(
            status_code=404,
            detail="ResearchStudy를 찾을 수 없습니다.",
        )

    return await get_store().list_sessions(study_id)