from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


# =========================================================
# 공통 Strict Model
# =========================================================

class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )


# =========================================================
# 공통 타입
# =========================================================

EvidenceStrength = Literal[
    "strong",
    "moderate",
    "weak",
]

Priority = Literal[
    "high",
    "medium",
    "low",
]

CoverageLevel = Literal[
    "high",
    "medium",
    "low",
    "not_covered",
]

OpportunitySource = Literal[
    "explicit_user_request",
    "derived_opportunity",
]


# =========================================================
# 1. 조사 전체 개요
# =========================================================

class StudyOverview(StrictModel):
    study_id: str

    research_title: str

    research_purpose: str

    participant_count: int

    completed_session_count: int

    question_count: int


# =========================================================
# 2. Executive Summary
# =========================================================

class StudySummaryPoint(StrictModel):
    point: str

    participant_count: int

    participant_ids: list[str]

    evidence_ids: list[str]


class StudyExecutiveSummary(StrictModel):
    core_insight: str

    summary: str

    key_takeaways: list[
        StudySummaryPoint
    ]


# =========================================================
# 3. Research Question Coverage
# =========================================================

class StudyQuestionCoverageItem(StrictModel):
    question_id: str

    question: str

    coverage: CoverageLevel

    participant_count: int

    covered_participant_count: int

    participant_ids: list[str]

    reason: str

    missing_information: list[str]


class StudyResearchCoverage(StrictModel):
    overall_coverage: CoverageLevel

    items: list[
        StudyQuestionCoverageItem
    ]


# =========================================================
# 4. Cross Interview Key Findings
# =========================================================

class CrossInterviewFinding(StrictModel):
    finding_id: str

    title: str

    summary: str

    evidence_strength: EvidenceStrength

    participant_count: int

    participant_ids: list[str]

    evidence_ids: list[str]


# =========================================================
# 5. Themes
# =========================================================

class StudyTheme(StrictModel):
    theme_id: str

    theme: str

    description: str

    participant_count: int

    participant_ids: list[str]

    evidence_ids: list[str]


# =========================================================
# 6. Drivers
# =========================================================

class StudyDriver(StrictModel):
    driver_id: str

    driver: str

    description: str

    strength: Priority

    participant_count: int

    participant_ids: list[str]

    evidence_ids: list[str]


# =========================================================
# 7. Pain Points
# =========================================================

class StudyPainPoint(StrictModel):
    pain_point_id: str

    title: str

    description: str

    severity: Priority

    participant_count: int

    participant_ids: list[str]

    evidence_ids: list[str]


# =========================================================
# 8. Needs
# =========================================================

class StudyNeed(StrictModel):
    need_id: str

    title: str

    description: str

    priority: Priority

    participant_count: int

    participant_ids: list[str]

    evidence_ids: list[str]


# =========================================================
# 9. Segment Differences
#
# 이제 단순히 "참여자 4명 이상"만 보는 게 아니라
# 실제 비교 그룹별 참여자까지 저장한다.
#
# 예:
#
# groups = [
#     {
#         "group_name": "고자율성 선호",
#         "participant_count": 4,
#         "participant_ids": [...]
#     },
#     {
#         "group_name": "변경 통제 우선",
#         "participant_count": 3,
#         "participant_ids": [...]
#     }
# ]
#
# 이후 Analyzer에서 각 그룹이 최소 2명인지
# 코드로 검증한다.
# =========================================================

class SegmentGroup(StrictModel):
    group_name: str

    group_description: str

    participant_count: int

    participant_ids: list[str]

    evidence_ids: list[str]


class SegmentInsight(StrictModel):
    segment_name: str

    segment_description: str

    groups: list[
        SegmentGroup
    ]

    participant_count: int

    participant_ids: list[str]

    key_difference: str

    evidence_ids: list[str]


# =========================================================
# 10. Opportunities
# =========================================================

class StudyOpportunity(StrictModel):
    opportunity_id: str

    opportunity: str

    source_type: OpportunitySource

    problem_or_need: str

    expected_value: str

    priority: Priority

    participant_count: int

    participant_ids: list[str]

    evidence_ids: list[str]


# =========================================================
# 11. Research Gaps
# =========================================================

class StudyResearchGap(StrictModel):
    topic: str

    reason: str

    priority: Priority


# =========================================================
# 12. Evidence Reference
# =========================================================

class StudyEvidenceReference(StrictModel):
    evidence_id: str

    participant_id: str

    session_id: str

    quote: str

    # JSON에는 항상 필드가 존재한다.
    # 특정 질문과 연결할 수 없을 때만 null.
    question_id: str | None


# =========================================================
# 최종 Study Report
#
# 이 구조 자체는 고정한다.
#
# 하지만:
# - 참여자 수
# - 질문 수
# - Finding 수
# - Theme 수
# - Segment 수
# - Opportunity 수
# - 조사 주제
#
# 는 Study마다 동적으로 달라진다.
# =========================================================

class StudyReportAnalysis(StrictModel):
    overview: StudyOverview

    executive_summary: StudyExecutiveSummary

    research_coverage: StudyResearchCoverage

    key_findings: list[
        CrossInterviewFinding
    ]

    themes: list[
        StudyTheme
    ]

    key_drivers: list[
        StudyDriver
    ]

    pain_points: list[
        StudyPainPoint
    ]

    needs: list[
        StudyNeed
    ]

    segment_differences: list[
        SegmentInsight
    ]

    opportunities: list[
        StudyOpportunity
    ]

    research_gaps: list[
        StudyResearchGap
    ]

    evidence: list[
        StudyEvidenceReference
    ]

    # 기본값을 주면 pydantic이 required에서 빼버리고, 그러면 Azure Structured
    # Outputs(strict)가 "모든 속성은 required여야 한다"며 요청을 400으로 거부한다.
    # 그 400은 폴백 로직상 "json_schema 미지원"으로 해석돼 스키마를 강제하지 않는
    # json_object 모드로 내려가고, 결국 모델이 섹션 일부만 만든 응답을 내놓아
    # "8 validation errors ... Field required"로 리포트 생성이 통째로 실패했다.
    # 값이 없을 때는 모델이 null을 채우도록 required로 유지한다.
    data_sufficiency_notice: str | None