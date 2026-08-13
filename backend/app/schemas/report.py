"""세션 종료 후 생성되는 AI 리포트 (§4.4, D6).

data의 내부 구조/형식(JSON 필드 구성, 텍스트, HTML 문자열 등)은 강제하지 않는다.
저장/조회를 위한 최소한의 겉봉투(envelope)만 정의 — 내용 설계는 담당자 몫.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.session import utcnow


class Report(BaseModel):
    session_id: str
    generated_at: datetime = Field(default_factory=utcnow)
    data: dict[str, Any]
