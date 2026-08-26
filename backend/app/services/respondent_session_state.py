"""Respondent-safe session metadata for the interview WebSocket channel."""

from __future__ import annotations

from typing import Any

from app.schemas.session import Session
from app.services.store import get_store


async def build_respondent_session_state(session: Session) -> dict[str, Any]:
    """Return session state with a project title kept separate from participant ID."""

    project_title: str | None = None
    if session.study_id:
        study = await get_store().get_study(session.study_id)
        if study is not None:
            project_title = study.title

    return {
        "id": session.id,
        "title": session.title,
        "project_title": project_title,
        "status": session.status,
        "duration_minutes": session.duration_minutes,
        "interpretation_language": session.interpretation_language,
        "questions": [question.model_dump(mode="json") for question in session.questions],
    }
