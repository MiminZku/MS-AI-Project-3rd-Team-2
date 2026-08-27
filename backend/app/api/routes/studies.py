from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import Response

from app.api.deps import require_admin
from app.api.download_responses import project_report_download_response
from app.schemas.project_report import ProjectAggregateReport
from app.schemas.session import QuestionNode, Session

from app.schemas.study import (
    ResearchStudy,
    ResearchStudyCreateRequest,
    ResearchStudyCreateResponse,
)
from app.services.ai.document_parser import get_document_parser
from app.services.question_script import parse_question_script
from app.services.report.slot_generator import get_slot_generator
from app.services.project_access import issue_project_access_id
from app.services.project_report import completed_real_sessions, start_project_report

from app.services.store import get_store
from app.services.storage import get_storage_service


logger = logging.getLogger(__name__)


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
    try:
        slot_generator = get_slot_generator()
        information_slots = await slot_generator.generate(
            title=payload.title,
            research_purpose=payload.research_purpose,
            question_script=payload.question_script,
            questions=questions,
        )
    except Exception as error:
        logger.warning("Information Slot generation skipped: %s", error)
        information_slots = []

    # 3. ResearchStudy 생성
    store = get_store()
    study = ResearchStudy(
        title=payload.title,
        access_id=await issue_project_access_id(store),
        research_purpose=payload.research_purpose,
        question_script=payload.question_script,
        questions=questions,
        information_slots=information_slots,
    )

    # 4. 저장
    await store.save_study(
        study
    )

    # 5. 반환
    return ResearchStudyCreateResponse(
        study=study
    )


# =========================================================
# Research Study 가이드라인 파일 업로드 및 자동 생성 (Word, PDF, MD)
# =========================================================

@router.post(
    "/upload-guide",
    response_model=ResearchStudyCreateResponse,
    status_code=201,
)
async def upload_guide_file(
    file: UploadFile = File(...),
) -> ResearchStudyCreateResponse:
    storage = get_storage_service()
    parser = get_document_parser()
    
    content = await file.read()
    filename = file.filename or "guide.md"
    
    # 1. 문서 파싱
    raw_text = parser.extract_text_from_bytes(content, filename)
    parsed = await parser.parse_guide(raw_text)
    
    # QuestionNode 변환
    questions = [
        QuestionNode(
            id=f"q{q.order}",
            order=q.order,
            text=q.text,
            branches=q.branches,
        )
        for q in parsed.questions
    ]
    
    # 2. Information Slot 생성
    try:
        slot_generator = get_slot_generator()
        information_slots = await slot_generator.generate(
            title=parsed.title,
            research_purpose=parsed.research_purpose,
            question_script=raw_text,
            questions=questions,
        )
    except Exception as e:
        logger.warning("Information Slot 생성 건너뜀: %s", e)
        information_slots = []
        
    store = get_store()
    study = ResearchStudy(
        title=parsed.title,
        access_id=await issue_project_access_id(store),
        research_purpose=parsed.research_purpose,
        question_script=raw_text,
        questions=questions,
        information_slots=information_slots,
    )
    
    # 3. Blob Storage에 원본 문서 업로드
    try:
        source_url = await storage.upload_file(
            file_bytes=content,
            filename=f"{study.id}/{filename}",
            content_type=file.content_type or "application/octet-stream",
            container_name="documents",
        )
    except Exception as e:
        logger.warning("문서 Blob Storage 업로드 실패: %s", e)
        
    # 4. Cosmos DB 저장
    await store.save_study(study)
    
    return ResearchStudyCreateResponse(study=study)


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
# Project aggregate report (PM only)
# =========================================================

@router.get("/{study_id}/aggregate-report", response_model=ProjectAggregateReport)
async def get_aggregate_report(study_id: str) -> ProjectAggregateReport:
    store = get_store()
    if await store.get_study(study_id) is None:
        raise HTTPException(status_code=404, detail="ResearchStudy를 찾을 수 없습니다.")
    report = await store.get_project_report(study_id)
    if report is not None:
        return report
    sessions = completed_real_sessions(await store.list_sessions(study_id))
    return ProjectAggregateReport(
        project_id=study_id,
        respondent_count=0,
        included_session_ids=[],
    )


@router.get("/{study_id}/aggregate-report/download", response_class=Response)
async def download_aggregate_report(
    study_id: str,
    format: str = Query("word", description="다운로드 파일 형식: word, powerbi, json"),
) -> Response:
    """생성된 프로젝트 리포트를 문서/데이터 파일로 내려받는다."""
    store = get_store()
    study = await store.get_study(study_id)
    if study is None:
        raise HTTPException(status_code=404, detail="ResearchStudy를 찾을 수 없습니다.")

    return project_report_download_response(
        study,
        await store.get_project_report(study_id),
        format=format,
    )


@router.post("/{study_id}/aggregate-report", response_model=ProjectAggregateReport)
async def create_aggregate_report(study_id: str) -> ProjectAggregateReport:
    """리포트 생성을 시작한다.

    응답자가 많으면 분석에 수 분이 걸려 HTTP 요청 안에서 끝낼 수 없다.
    시작만 하고 GENERATING 스냅샷을 바로 돌려주며, 호출자는 GET으로 완료를 확인한다.
    """
    try:
        report = await start_project_report(study_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    if report.status == "FAILED":
        # 분석 모델 호출 실패 메시지에 404 같은 상태코드가 섞여 나오면 "페이지 없음"으로
        # 오해하기 쉽다. 어느 단계에서 실패했는지 앞에 붙여 준다.
        detail = "프로젝트 리포트 생성에 실패했습니다."
        if report.error_message:
            detail = f"{detail} (분석 단계 오류: {report.error_message})"
        raise HTTPException(status_code=500, detail=detail)

    return report


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
# Research Study 삭제 (산하 세션도 함께 삭제)
# =========================================================

@router.delete(
    "/{study_id}",
    status_code=204,
)
async def delete_study(
    study_id: str,
) -> None:

    store = get_store()

    study = await store.get_study(study_id)
    if study is None:
        raise HTTPException(
            status_code=404,
            detail="ResearchStudy를 찾을 수 없습니다.",
        )

    sessions = await store.list_sessions(study_id)
    for session in sessions:
        await store.delete_session(session.id)

    await store.delete_study(study_id)


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
