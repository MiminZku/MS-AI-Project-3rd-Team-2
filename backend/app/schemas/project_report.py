from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.session import utcnow


ProjectReportStatus = Literal[
    "NOT_GENERATED",
    "GENERATING",
    "COMPLETED",
    "FAILED",
]


class ProjectAggregateReport(BaseModel):
    """PM이 명시적으로 생성한 프로젝트 단위 리포트 스냅샷."""

    project_id: str
    status: ProjectReportStatus = "NOT_GENERATED"
    generated_at: datetime | None = None
    included_session_ids: list[str] = Field(default_factory=list)
    respondent_count: int = 0
    content: dict[str, Any] | None = None
    error_message: str | None = None
    updated_at: datetime = Field(default_factory=utcnow)
