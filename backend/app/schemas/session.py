"""세션 / 질문트리 / 대화턴 / 참관자 지시 도메인 모델."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

SessionStatus = Literal["created", "running", "ended"]
InstructionStatus = Literal["queued", "applied"]
Speaker = Literal["interviewee", "assistant"]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class QuestionNode(BaseModel):
    """메인 질문 1개 + 답변 조건별 파생질문 분기 (§4.2)."""

    id: str
    order: int
    text: str
    # {"부담됨": "그 때문에 주문을 포기한 경험이 있나요?"}
    branches: dict[str, str] = Field(default_factory=dict)


class Session(BaseModel):
    id: str = Field(default_factory=lambda: new_id("ses"))
    study_id: str | None = None
    title: str = "제목 없는 인터뷰"
    status: SessionStatus = "created"
    duration_minutes: int = 20
    questions: list[QuestionNode] = Field(default_factory=list)
    current_question_index: int = 0
    # current_question_index의 메인 질문을 응답자에게 실제로 물었는지 여부.
    # False면 파생질문/전이보다 메인 질문 발화가 우선한다 (파생질문 선행 방지).
    main_question_asked: bool = False
    probe_count: int = 0
    completed_question_indices: list[int] = Field(default_factory=list)
    covered_facts: dict[str, str] = Field(default_factory=dict)
    active_branch: str | None = None
    taken_branches: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    video_recording_url: str | None = None
    audio_recording_url: str | None = None
        # PM 시나리오/가상 응답자 데이터는 실제 프로젝트 종합 리포트에서 제외한다.
    is_simulation: bool = False

    def covered_count(self) -> int:
        return min(len(self.completed_question_indices), len(self.questions))





class Turn(BaseModel):
    index: int
    speaker: Speaker
    text: str
    text_en: str | None = None
    # AI 판단 근거. 참관자 전용이며 인터뷰이에게 절대 전송하지 않는다 (C5).
    rationale: str | None = None
    # 이 턴에 주입된 참관자 지시 id (있는 경우)
    instruction_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class Instruction(BaseModel):
    id: str = Field(default_factory=lambda: new_id("ins"))
    session_id: str
    text: str
    status: InstructionStatus = "queued"
    created_at: datetime = Field(default_factory=utcnow)
    applied_at: datetime | None = None
    # 주입된 턴 번호
    applied_turn: int | None = None


class SessionCreateRequest(BaseModel):
    study_id: str | None = None
    title: str = "제목 없는 인터뷰"
    duration_minutes: int = 20
    # §4.2의 텍스트 포맷. 파싱해서 questions로 변환된다.
    question_script: str = ""


class SessionCreateResponse(BaseModel):
    session: Session
    # 응답자에게 전달할 인터뷰 링크
    interviewee_url: str
