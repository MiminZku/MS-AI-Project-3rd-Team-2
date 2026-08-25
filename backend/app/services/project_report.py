from __future__ import annotations

import logging
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


async def generate_project_report(project_id: str) -> ProjectAggregateReport:
    """Create one explicit PM-requested aggregate snapshot for a project."""
    store = get_store()
    study = await store.get_study(project_id)
    if study is None:
        raise LookupError("프로젝트를 찾을 수 없습니다.")

    existing = await store.get_project_report(project_id)
    if existing and existing.status == "GENERATING":
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
                report = await individual_report_generator.generate(
                    session,
                    transcripts[session.id],
                    await store.list_instructions(session.id),
                )
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
