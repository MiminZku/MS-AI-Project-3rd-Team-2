from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.session import QuestionNode, new_id, utcnow


SlotImportance = Literal[
    "high",
    "medium",
    "low",
]


class InformationSlot(BaseModel):
    """
    인터뷰에서 반드시 확보해야 하는 정보 단위.

    예:
    - 현재 사용 도구
    - 선택 이유
    - Pain Point
    - 비용 영향
    - Switching Trigger
    """

    slot_id: str

    # 어떤 질문과 주로 연결되는 정보인지
    question_id: str

    # 사람이 화면에서 볼 이름
    slot_name: str

    # 이 Slot에서 실제로 알고 싶은 정보
    description: str

    importance: SlotImportance = "medium"


class ResearchStudy(BaseModel):
    """
    여러 참가자 인터뷰가 공통으로 사용하는
    하나의 조사 프로젝트.
    """

    id: str = Field(
        default_factory=lambda: new_id("study")
    )

    title: str

    # PM이 Client에게 전달하는 비추측형 프로젝트 접속 코드.
    # 기존 프로젝트 문서는 마이그레이션 중일 수 있으므로 optional로 읽고,
    # 새 프로젝트와 시작 시 보정되는 기존 프로젝트에는 항상 값이 저장된다.
    access_id: str | None = None

    research_purpose: str

    # 기업/연구자가 입력한 원본 질문지
    question_script: str

    # question_script를 파싱한 질문
    questions: list[QuestionNode] = Field(
        default_factory=list
    )

    # 질문지와 조사 목적을 기반으로
    # AI가 한 번 생성한 공통 Information Slot
    information_slots: list[InformationSlot] = Field(
        default_factory=list
    )

    created_at: datetime = Field(
        default_factory=utcnow
    )


class ResearchStudyCreateRequest(BaseModel):
    title: str

    research_purpose: str

    question_script: str


class ResearchStudyCreateResponse(BaseModel):
    study: ResearchStudy
