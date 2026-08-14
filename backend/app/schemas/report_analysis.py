from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


# =========================================================
# 공통 Strict Model
# =========================================================

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# =========================================================
# Participant Context
# =========================================================

class UsagePattern(StrictModel):
    situation: str
    preferred_tool: str
    evidence_ids: list[str]


class ParticipantContext(StrictModel):
    primary_tool: str
    secondary_tools: list[str]
    usage_pattern: list[UsagePattern]


# =========================================================
# Executive Summary
# =========================================================

class ExecutiveSummary(StrictModel):
    core_insight: str
    current_preference: str
    primary_driver: str
    primary_pain_point: str
    top_switching_trigger: str


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
# Preference Drivers
# =========================================================

class PreferenceDriver(StrictModel):
    driver: str

    strength: Literal[
        "high",
        "medium",
        "low",
    ]

    description: str
    evidence_ids: list[str]


# =========================================================
# Pain Points
# =========================================================

class PainPoint(StrictModel):
    pain_point: str

    severity: Literal[
        "high",
        "medium",
        "low",
    ]

    situation: str
    user_impact: str
    evidence_ids: list[str]


# =========================================================
# Switching Analysis
# =========================================================

class RetentionDriver(StrictModel):
    driver: str
    evidence_ids: list[str]


class SwitchingBarrier(StrictModel):
    barrier: str
    evidence_ids: list[str]


class SwitchingTrigger(StrictModel):
    trigger: str
    evidence_ids: list[str]


class SwitchingAnalysis(StrictModel):
    retention_drivers: list[RetentionDriver]
    switching_barriers: list[SwitchingBarrier]
    switching_triggers: list[SwitchingTrigger]

    switching_signal: Literal[
        "strong",
        "moderate",
        "weak",
        "unclear",
    ]


# =========================================================
# Feature Opportunities
# =========================================================

class FeatureOpportunity(StrictModel):
    feature: str

    source_type: Literal[
        "explicit_user_request",
        "derived_opportunity",
    ]

    problem: str
    user_need: str
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

class ObserverInterventionAnalysis(StrictModel):
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
    mode: Literal["azure_openai"]


# =========================================================
# 최종 Individual Interview Analysis
# =========================================================

class IndividualInterviewAnalysis(StrictModel):
    participant_context: ParticipantContext

    executive_summary: ExecutiveSummary

    research_coverage: ResearchCoverage

    slot_coverage: SlotCoverage

    key_findings: list[KeyFinding]

    preference_drivers: list[PreferenceDriver]

    pain_points: list[PainPoint]

    switching_analysis: SwitchingAnalysis

    feature_opportunities: list[FeatureOpportunity]

    observer_intervention_analysis: list[
        ObserverInterventionAnalysis
    ]

    researcher_attention: list[
        ResearcherAttention
    ]

    analysis_metadata: AnalysisMetadata