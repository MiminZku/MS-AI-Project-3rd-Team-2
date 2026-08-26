from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from app.core.config import get_settings
from app.schemas.project_report import ProjectAggregateReport
from app.schemas.session import Session, utcnow
from app.schemas.study import ResearchStudy
from app.services.report import generator as individual_report_generator
from app.services.report.study_analyzer import get_study_report_analyzer
from app.services.store import get_store

logger = logging.getLogger(__name__)


def completed_real_sessions(sessions: list[Session]) -> list[Session]:
    """Only actual, completed respondent interviews belong to a project report."""
    return [
        session
        for session in sessions
        if session.status == "ended" and not session.is_simulation
    ]


def _local_aggregate_content(
    study: ResearchStudy,
    sessions: list[Session],
    transcripts: dict[str, list[Any]],
) -> dict[str, Any]:
    """Useful local fallback when Azure analysis is intentionally not configured."""
    session_rows = []
    evidence = []
    for session in sessions:
        answers = [
            {
                "turn": turn.index,
                "answer": turn.text,
                "created_at": turn.created_at.isoformat(),
            }
            for turn in transcripts[session.id]
            if turn.speaker == "interviewee" and turn.text.strip()
        ]
        session_rows.append(
            {
                "session_id": session.id,
                "respondent_id": session.title,
                "answers": answers,
            }
        )
        evidence.extend(
            {
                "session_id": session.id,
                "respondent_id": session.title,
                "quote": answer["answer"],
                "turn": answer["turn"],
            }
            for answer in answers
        )

    caution = (
        "현재 완료된 인터뷰가 1건이므로 결과를 일반화하기 어렵습니다."
        if len(sessions) == 1
        else None
    )
    return {
        "overview": {
            "study_id": study.id,
            "research_title": study.title,
            "research_purpose": study.research_purpose,
            "participant_count": len(sessions),
            "completed_session_count": len(sessions),
            "question_count": len(study.questions),
        },
        "data_sufficiency_notice": caution,
        "sessions": session_rows,
        "evidence": evidence,
        "analysis_mode": "local_transcript_snapshot",
    }


# GENERATING 상태로 이 시간 넘게 멈춰 있으면, 앞선 실행이 중간에 죽은 것으로 보고
# 다시 시작할 수 있게 한다. 이 장치가 없으면 요청이 한 번 끊기는 순간
# 그 프로젝트는 영원히 "생성 중"에 갇혀 리포트를 만들 수 없다.
STALE_GENERATING_AFTER = timedelta(minutes=20)


def _is_stale(report: ProjectAggregateReport) -> bool:
    return utcnow() - report.updated_at > STALE_GENERATING_AFTER


async def start_project_report(project_id: str) -> ProjectAggregateReport:
    """리포트 생성을 시작하고 GENERATING 스냅샷을 즉시 돌려준다.

    18명 분량이면 개별 분석만으로도 수 분이 걸려 HTTP 요청 안에서 끝낼 수 없다.
    (실제로 응답 대기 중 연결이 끊겨 브라우저에 "Failed to fetch"가 떴다.)
    실제 생성은 백그라운드에서 돌리고, 호출자는 GET으로 상태를 폴링한다.
    """
    store = get_store()
    study = await store.get_study(project_id)
    if study is None:
        raise LookupError("프로젝트를 찾을 수 없습니다.")

    existing = await store.get_project_report(project_id)
    if existing and existing.status == "GENERATING" and not _is_stale(existing):
        return existing

    sessions = completed_real_sessions(await store.list_sessions(project_id))
    if not sessions:
        raise ValueError("완료된 인터뷰가 없어 리포트를 생성할 수 없습니다.")

    generating = ProjectAggregateReport(
        project_id=project_id,
        status="GENERATING",
        included_session_ids=[session.id for session in sessions],
        respondent_count=len(sessions),
        updated_at=utcnow(),
    )
    await store.save_project_report(generating)

    asyncio.create_task(_run_project_report_safely(project_id))
    return generating


async def _run_project_report_safely(project_id: str) -> None:
    """백그라운드 실행 래퍼. 예외가 새어 나가 태스크가 조용히 죽지 않게 한다."""
    try:
        await generate_project_report(project_id)
    except Exception:
        logger.exception("프로젝트 리포트 백그라운드 생성 실패 project=%s", project_id)


async def generate_project_report(project_id: str) -> ProjectAggregateReport:
    """Create one explicit PM-requested aggregate snapshot for a project."""
    store = get_store()
    study = await store.get_study(project_id)
    if study is None:
        raise LookupError("프로젝트를 찾을 수 없습니다.")

    sessions = completed_real_sessions(await store.list_sessions(project_id))
    if not sessions:
        raise ValueError("완료된 인터뷰가 없어 리포트를 생성할 수 없습니다.")

    generating = ProjectAggregateReport(
        project_id=project_id,
        status="GENERATING",
        included_session_ids=[session.id for session in sessions],
        respondent_count=len(sessions),
        updated_at=utcnow(),
    )
    await store.save_project_report(generating)

    try:
        transcripts = {
            session.id: await store.get_transcript(session.id)
            for session in sessions
        }
        settings = get_settings()
        if not settings.use_azure_openai:
            content = _local_aggregate_content(study, sessions, transcripts)
        else:
            participant_reports = []
            for session in sessions:
                # 이미 만들어 둔 개별 리포트가 있으면 재사용한다. 중간에 실패해 다시
                # 돌릴 때 18명 분석을 처음부터 다시 하지 않게 해 준다.
                report = await store.get_report(session.id)
                if report is None:
                    report = await individual_report_generator.generate(
                        session,
                        transcripts[session.id],
                        await store.list_instructions(session.id),
                    )
                    await store.save_report(report)
                participant_reports.append(report.model_dump(mode="json"))
            content = (await get_study_report_analyzer().analyze(study, participant_reports)).model_dump(mode="json")
            if len(sessions) == 1:
                content["data_sufficiency_notice"] = "현재 완료된 인터뷰가 1건이므로 결과를 일반화하기 어렵습니다."

        completed = ProjectAggregateReport(
            project_id=project_id,
            status="COMPLETED",
            generated_at=utcnow(),
            included_session_ids=[session.id for session in sessions],
            respondent_count=len(sessions),
            content=content,
            updated_at=utcnow(),
        )
        await store.save_project_report(completed)
        return completed
    except Exception as exc:
        logger.exception("Project aggregate report generation failed project=%s", project_id)
        failed = ProjectAggregateReport(
            project_id=project_id,
            status="FAILED",
            included_session_ids=[session.id for session in sessions],
            respondent_count=len(sessions),
            error_message=str(exc),
            updated_at=utcnow(),
        )
        await store.save_project_report(failed)
        return failed
