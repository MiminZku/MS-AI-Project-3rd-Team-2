from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


# =========================================================
# 공통 Strict Model
# =========================================================

class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )


# =========================================================
# Participant Context
#
# 특정 "도구", "제품"에 고정하지 않는다.
#
# 예:
# - 직무: 백엔드 개발자
# - 이용 빈도: 주 3회
# - 주 사용 서비스: A 서비스
# - 경험 기간: 2년
# =========================================================

class ContextAttribute(StrictModel):
    name: str
    value: str
    evidence_ids: list[str]


class ParticipantContext(StrictModel):
    summary: str
    attributes: list[ContextAttribute]


# =========================================================
# Executive Summary
# =========================================================

class SummaryPoint(StrictModel):
    point: str
    evidence_ids: list[str]


class ExecutiveSummary(StrictModel):
    core_insight: str
    summary: str
    key_takeaways: list[SummaryPoint]


# =========================================================
# Question Coverage
# =========================================================

class CoverageItem(StrictModel):
    question_id: str
    question: str

    coverage: Literal[
        "high",
        "medium",
        "low",
        "not_covered",
    ]

    reason: str
    evidence_ids: list[str]
    missing_information: list[str]


class ResearchCoverage(StrictModel):
    overall_coverage: Literal[
        "high",
        "medium",
        "low",
    ]

    items: list[CoverageItem]


# =========================================================
# Slot Coverage
#
# Study 생성 시 질문지에 따라 자동 생성된
# Information Slot을 그대로 평가한다.
# =========================================================

class SlotCoverageItem(StrictModel):
    slot_id: str
    question_id: str
    slot_name: str

    coverage: Literal[
        "high",
        "medium",
        "low",
        "not_covered",
    ]

    reason: str
    evidence_ids: list[str]
    missing_information: list[str]


class SlotCoverage(StrictModel):
    overall_coverage: Literal[
        "high",
        "medium",
        "low",
    ]

    items: list[SlotCoverageItem]


# =========================================================
# Key Findings
# =========================================================

class KeyFinding(StrictModel):
    title: str
    summary: str

    evidence_strength: Literal[
        "strong",
        "moderate",
        "weak",
    ]

    evidence_ids: list[str]


# =========================================================
# Themes
#
# 인터뷰에서 반복되거나
# 조사 목적상 의미 있는 주제
# =========================================================

class Theme(StrictModel):
    theme: str
    description: str
    evidence_ids: list[str]


# =========================================================
# Key Drivers
#
# 특정 "선호"에만 한정하지 않는다.
#
# 구매 요인
# 만족 요인
# 선택 요인
# 행동 요인
# 재방문 요인 등 모두 가능
# =========================================================

class KeyDriver(StrictModel):
    driver: str

    strength: Literal[
        "high",
        "medium",
        "low",
    ]

    description: str
    evidence_ids: list[str]


# =========================================================
# Needs / Pain Points
# =========================================================

class NeedOrPainPoint(StrictModel):
    type: Literal[
        "pain_point",
        "need",
    ]

    title: str

    severity: Literal[
        "high",
        "medium",
        "low",
    ]

    situation: str
    impact: str
    evidence_ids: list[str]


# =========================================================
# Decision / Behavior Dynamics
#
# 구매, 선택, 유지, 이탈, 전환 등의
# 의사결정 행동이 실제 조사에 있을 때만 사용.
#
# 관련 없는 조사라면
# decision_dynamics = null
# =========================================================

class DecisionFactor(StrictModel):
    factor: str
    description: str
    evidence_ids: list[str]


class DecisionBarrier(StrictModel):
    barrier: str
    evidence_ids: list[str]


class DecisionTrigger(StrictModel):
    trigger: str
    evidence_ids: list[str]


class DecisionDynamics(StrictModel):
    current_state: str

    decision_factors: list[
        DecisionFactor
    ]

    barriers: list[
        DecisionBarrier
    ]

    triggers: list[
        DecisionTrigger
    ]

    behavioral_signal: Literal[
        "strong",
        "moderate",
        "weak",
        "unclear",
    ]


# =========================================================
# Opportunities
#
# Feature에만 한정하지 않는다.
# 제품 / 서비스 / 프로세스 / 정책 /
# 커뮤니케이션 / 추가 연구 등 모두 가능
# =========================================================

class Opportunity(StrictModel):
    opportunity: str

    opportunity_type: Literal[
        "product",
        "service",
        "process",
        "policy",
        "communication",
        "research",
        "other",
    ]

    source_type: Literal[
        "explicit_user_request",
        "derived_opportunity",
    ]

    problem_or_need: str
    expected_value: str

    priority: Literal[
        "high",
        "medium",
        "low",
    ]

    evidence_ids: list[str]


# =========================================================
# Observer Intervention Analysis
# =========================================================

class ObserverInterventionAnalysis(
    StrictModel
):
    instruction_id: str
    instruction: str
    applied_turn: int

    resulting_evidence_ids: list[str]

    research_value: Literal[
        "high",
        "medium",
        "low",
    ]

    impact: str


# =========================================================
# Researcher Attention
#
# 다음 인터뷰 / 추가 확인이 필요한 내용
# =========================================================

class ResearcherAttention(StrictModel):
    topic: str
    reason: str

    priority: Literal[
        "high",
        "medium",
        "low",
    ]


# =========================================================
# Analysis Metadata
# =========================================================

class AnalysisMetadata(StrictModel):
    mode: Literal[
        "azure_openai"
    ]


# =========================================================
# 최종 범용 Individual Interview Analysis
# =========================================================

class IndividualInterviewAnalysis(
    StrictModel
):
    participant_context: ParticipantContext

    executive_summary: ExecutiveSummary

    research_coverage: ResearchCoverage

    slot_coverage: SlotCoverage

    key_findings: list[
        KeyFinding
    ]

    themes: list[
        Theme
    ]

    key_drivers: list[
        KeyDriver
    ]

    needs_and_pain_points: list[
        NeedOrPainPoint
    ]

    decision_dynamics: (
        DecisionDynamics | None
    )

    opportunities: list[
        Opportunity
    ]

    observer_intervention_analysis: list[
        ObserverInterventionAnalysis
    ]

    researcher_attention: list[
        ResearcherAttention
    ]

    analysis_metadata: AnalysisMetadata