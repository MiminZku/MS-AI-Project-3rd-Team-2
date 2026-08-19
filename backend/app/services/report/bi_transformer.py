from __future__ import annotations

from typing import Any

from app.schemas.study_report import StudyReportAnalysis


class StudyReportBITransformer:
    """
    StudyReportAnalysis를
    Power BI / Web Dashboard에서 사용하기 쉬운
    범용 정규화 테이블 구조로 변환한다.

    특정 조사 주제, 질문 수, 참여자 수에 종속되지 않는다.

    핵심 고유키
    ----------
    participant_key
        study_id + participant_id

    evidence_key
        study_id + evidence_id

    insight_key
        study_id + insight_type + insight_id

    segment_key
        study_id + segment_id

    group_key
        study_id + group_id
    """

    # =====================================================
    # Main
    # =====================================================

    def transform(
        self,
        report: StudyReportAnalysis,
    ) -> dict[str, list[dict[str, Any]]]:

        tables: dict[
            str,
            list[dict[str, Any]],
        ] = {
            "studies": [],
            "participants": [],
            "coverage": [],
            "insights": [],
            "insight_participants": [],
            "insight_evidence": [],
            "segments": [],
            "segment_groups": [],
            "segment_group_participants": [],
            "segment_group_evidence": [],
            "evidence": [],
        }

        study_id = (
            report.overview.study_id
        )

        self._add_study(
            tables=tables,
            report=report,
        )

        self._add_participants(
            tables=tables,
            report=report,
            study_id=study_id,
        )

        self._add_coverage(
            tables=tables,
            report=report,
            study_id=study_id,
        )

        self._add_executive_takeaways(
            tables=tables,
            report=report,
            study_id=study_id,
        )

        self._add_key_findings(
            tables=tables,
            report=report,
            study_id=study_id,
        )

        self._add_themes(
            tables=tables,
            report=report,
            study_id=study_id,
        )

        self._add_drivers(
            tables=tables,
            report=report,
            study_id=study_id,
        )

        self._add_pain_points(
            tables=tables,
            report=report,
            study_id=study_id,
        )

        self._add_needs(
            tables=tables,
            report=report,
            study_id=study_id,
        )

        self._add_opportunities(
            tables=tables,
            report=report,
            study_id=study_id,
        )

        self._add_research_gaps(
            tables=tables,
            report=report,
            study_id=study_id,
        )

        self._add_segments(
            tables=tables,
            report=report,
            study_id=study_id,
        )

        self._add_evidence(
            tables=tables,
            report=report,
            study_id=study_id,
        )

        return tables

    # =====================================================
    # Study
    # =====================================================

    def _add_study(
        self,
        tables: dict[
            str,
            list[dict[str, Any]],
        ],
        report: StudyReportAnalysis,
    ) -> None:

        overview = report.overview

        tables["studies"].append(
            {
                "study_id": (
                    overview.study_id
                ),

                "research_title": (
                    overview.research_title
                ),

                "research_purpose": (
                    overview.research_purpose
                ),

                "participant_count": (
                    overview.participant_count
                ),

                "completed_session_count": (
                    overview.completed_session_count
                ),

                "question_count": (
                    overview.question_count
                ),

                "overall_coverage": (
                    report
                    .research_coverage
                    .overall_coverage
                ),

                "core_insight": (
                    report
                    .executive_summary
                    .core_insight
                ),

                "executive_summary": (
                    report
                    .executive_summary
                    .summary
                ),
            }
        )

    # =====================================================
    # Participants
    #
    # Study마다 P01이 다시 생길 수 있으므로
    # participant_id 자체를 Power BI 고유키로 쓰지 않는다.
    #
    # participant_key:
    #
    # study_001::P01
    # study_002::P01
    #
    # 는 서로 다른 사람이 된다.
    # =====================================================

    def _add_participants(
        self,
        tables: dict[
            str,
            list[dict[str, Any]],
        ],
        report: StudyReportAnalysis,
        study_id: str,
    ) -> None:

        participant_ids: list[str] = []

        for evidence in report.evidence:

            participant_id = (
                evidence.participant_id
            )

            if (
                participant_id
                not in participant_ids
            ):
                participant_ids.append(
                    participant_id
                )

        for participant_id in (
            participant_ids
        ):

            tables["participants"].append(
                {
                    "study_id": (
                        study_id
                    ),

                    "participant_key": (
                        self._participant_key(
                            study_id=study_id,
                            participant_id=(
                                participant_id
                            ),
                        )
                    ),

                    "participant_id": (
                        participant_id
                    ),
                }
            )

    # =====================================================
    # Research Coverage
    # =====================================================

    def _add_coverage(
        self,
        tables: dict[
            str,
            list[dict[str, Any]],
        ],
        report: StudyReportAnalysis,
        study_id: str,
    ) -> None:

        for index, item in enumerate(
            report.research_coverage.items,
            start=1,
        ):

            coverage_id = (
                f"{study_id}_coverage_{index:03d}"
            )

            tables["coverage"].append(
                {
                    "study_id": (
                        study_id
                    ),

                    "coverage_id": (
                        coverage_id
                    ),

                    "question_id": (
                        item.question_id
                    ),

                    "question": (
                        item.question
                    ),

                    "coverage": (
                        item.coverage
                    ),

                    "participant_count": (
                        item.participant_count
                    ),

                    "covered_participant_count": (
                        item
                        .covered_participant_count
                    ),

                    "coverage_rate": (
                        self._safe_ratio(
                            item
                            .covered_participant_count,
                            item.participant_count,
                        )
                    ),

                    "reason": (
                        item.reason
                    ),

                    "missing_information": (
                        self._join_text(
                            item.missing_information
                        )
                    ),
                }
            )

    # =====================================================
    # Executive Takeaways
    # =====================================================

    def _add_executive_takeaways(
        self,
        tables: dict[
            str,
            list[dict[str, Any]],
        ],
        report: StudyReportAnalysis,
        study_id: str,
    ) -> None:

        for index, item in enumerate(
            report
            .executive_summary
            .key_takeaways,
            start=1,
        ):

            insight_id = (
                f"ET{index:03d}"
            )

            self._add_insight(
                tables=tables,
                study_id=study_id,
                insight_type=(
                    "executive_takeaway"
                ),
                insight_id=(
                    insight_id
                ),
                title=(
                    item.point
                ),
                description=(
                    item.point
                ),
                participant_count=(
                    item.participant_count
                ),
                participant_ids=(
                    item.participant_ids
                ),
                evidence_ids=(
                    item.evidence_ids
                ),
                strength=None,
                priority=None,
                source_type=None,
                expected_value=None,
            )

    # =====================================================
    # Findings
    # =====================================================

    def _add_key_findings(
        self,
        tables: dict[
            str,
            list[dict[str, Any]],
        ],
        report: StudyReportAnalysis,
        study_id: str,
    ) -> None:

        for item in report.key_findings:

            self._add_insight(
                tables=tables,
                study_id=study_id,
                insight_type=(
                    "key_finding"
                ),
                insight_id=(
                    item.finding_id
                ),
                title=(
                    item.title
                ),
                description=(
                    item.summary
                ),
                participant_count=(
                    item.participant_count
                ),
                participant_ids=(
                    item.participant_ids
                ),
                evidence_ids=(
                    item.evidence_ids
                ),
                strength=(
                    item.evidence_strength
                ),
                priority=None,
                source_type=None,
                expected_value=None,
            )

    # =====================================================
    # Themes
    # =====================================================

    def _add_themes(
        self,
        tables: dict[
            str,
            list[dict[str, Any]],
        ],
        report: StudyReportAnalysis,
        study_id: str,
    ) -> None:

        for item in report.themes:

            self._add_insight(
                tables=tables,
                study_id=study_id,
                insight_type="theme",
                insight_id=(
                    item.theme_id
                ),
                title=(
                    item.theme
                ),
                description=(
                    item.description
                ),
                participant_count=(
                    item.participant_count
                ),
                participant_ids=(
                    item.participant_ids
                ),
                evidence_ids=(
                    item.evidence_ids
                ),
                strength=None,
                priority=None,
                source_type=None,
                expected_value=None,
            )

    # =====================================================
    # Drivers
    # =====================================================

    def _add_drivers(
        self,
        tables: dict[
            str,
            list[dict[str, Any]],
        ],
        report: StudyReportAnalysis,
        study_id: str,
    ) -> None:

        for item in report.key_drivers:

            self._add_insight(
                tables=tables,
                study_id=study_id,
                insight_type="driver",
                insight_id=(
                    item.driver_id
                ),
                title=(
                    item.driver
                ),
                description=(
                    item.description
                ),
                participant_count=(
                    item.participant_count
                ),
                participant_ids=(
                    item.participant_ids
                ),
                evidence_ids=(
                    item.evidence_ids
                ),
                strength=(
                    item.strength
                ),
                priority=None,
                source_type=None,
                expected_value=None,
            )

    # =====================================================
    # Pain Points
    # =====================================================

    def _add_pain_points(
        self,
        tables: dict[
            str,
            list[dict[str, Any]],
        ],
        report: StudyReportAnalysis,
        study_id: str,
    ) -> None:

        for item in report.pain_points:

            self._add_insight(
                tables=tables,
                study_id=study_id,
                insight_type=(
                    "pain_point"
                ),
                insight_id=(
                    item.pain_point_id
                ),
                title=(
                    item.title
                ),
                description=(
                    item.description
                ),
                participant_count=(
                    item.participant_count
                ),
                participant_ids=(
                    item.participant_ids
                ),
                evidence_ids=(
                    item.evidence_ids
                ),
                strength=None,
                priority=(
                    item.severity
                ),
                source_type=None,
                expected_value=None,
            )

    # =====================================================
    # Needs
    # =====================================================

    def _add_needs(
        self,
        tables: dict[
            str,
            list[dict[str, Any]],
        ],
        report: StudyReportAnalysis,
        study_id: str,
    ) -> None:

        for item in report.needs:

            self._add_insight(
                tables=tables,
                study_id=study_id,
                insight_type="need",
                insight_id=(
                    item.need_id
                ),
                title=(
                    item.title
                ),
                description=(
                    item.description
                ),
                participant_count=(
                    item.participant_count
                ),
                participant_ids=(
                    item.participant_ids
                ),
                evidence_ids=(
                    item.evidence_ids
                ),
                strength=None,
                priority=(
                    item.priority
                ),
                source_type=None,
                expected_value=None,
            )

    # =====================================================
    # Opportunities
    # =====================================================

    def _add_opportunities(
        self,
        tables: dict[
            str,
            list[dict[str, Any]],
        ],
        report: StudyReportAnalysis,
        study_id: str,
    ) -> None:

        for item in report.opportunities:

            self._add_insight(
                tables=tables,
                study_id=study_id,
                insight_type=(
                    "opportunity"
                ),
                insight_id=(
                    item.opportunity_id
                ),
                title=(
                    item.opportunity
                ),
                description=(
                    item.problem_or_need
                ),
                participant_count=(
                    item.participant_count
                ),
                participant_ids=(
                    item.participant_ids
                ),
                evidence_ids=(
                    item.evidence_ids
                ),
                strength=None,
                priority=(
                    item.priority
                ),
                source_type=(
                    item.source_type
                ),
                expected_value=(
                    item.expected_value
                ),
            )

    # =====================================================
    # Research Gaps
    # =====================================================

    def _add_research_gaps(
        self,
        tables: dict[
            str,
            list[dict[str, Any]],
        ],
        report: StudyReportAnalysis,
        study_id: str,
    ) -> None:

        for index, item in enumerate(
            report.research_gaps,
            start=1,
        ):

            insight_id = (
                f"RG{index:03d}"
            )

            insight_key = (
                self._insight_key(
                    study_id=study_id,
                    insight_type=(
                        "research_gap"
                    ),
                    insight_id=(
                        insight_id
                    ),
                )
            )

            tables["insights"].append(
                {
                    "study_id": (
                        study_id
                    ),

                    "insight_key": (
                        insight_key
                    ),

                    "insight_type": (
                        "research_gap"
                    ),

                    "insight_id": (
                        insight_id
                    ),

                    "title": (
                        item.topic
                    ),

                    "description": (
                        item.reason
                    ),

                    "participant_count": 0,

                    "strength": None,

                    "priority": (
                        item.priority
                    ),

                    "source_type": None,

                    "expected_value": None,
                }
            )

    # =====================================================
    # Generic Insight
    # =====================================================

    def _add_insight(
        self,
        tables: dict[
            str,
            list[dict[str, Any]],
        ],
        study_id: str,
        insight_type: str,
        insight_id: str,
        title: str,
        description: str,
        participant_count: int,
        participant_ids: list[str],
        evidence_ids: list[str],
        strength: str | None,
        priority: str | None,
        source_type: str | None,
        expected_value: str | None,
    ) -> None:

        insight_key = (
            self._insight_key(
                study_id=study_id,
                insight_type=(
                    insight_type
                ),
                insight_id=(
                    insight_id
                ),
            )
        )

        tables["insights"].append(
            {
                "study_id": (
                    study_id
                ),

                "insight_key": (
                    insight_key
                ),

                "insight_type": (
                    insight_type
                ),

                "insight_id": (
                    insight_id
                ),

                "title": (
                    title
                ),

                "description": (
                    description
                ),

                "participant_count": (
                    participant_count
                ),

                "strength": (
                    strength
                ),

                "priority": (
                    priority
                ),

                "source_type": (
                    source_type
                ),

                "expected_value": (
                    expected_value
                ),
            }
        )

        # ---------------------------------------------
        # Insight ↔ Participant
        # ---------------------------------------------

        for participant_id in (
            participant_ids
        ):

            tables[
                "insight_participants"
            ].append(
                {
                    "study_id": (
                        study_id
                    ),

                    "insight_key": (
                        insight_key
                    ),

                    "insight_type": (
                        insight_type
                    ),

                    "insight_id": (
                        insight_id
                    ),

                    "participant_key": (
                        self._participant_key(
                            study_id=study_id,
                            participant_id=(
                                participant_id
                            ),
                        )
                    ),

                    "participant_id": (
                        participant_id
                    ),
                }
            )

        # ---------------------------------------------
        # Insight ↔ Evidence
        # ---------------------------------------------

        for evidence_id in (
            evidence_ids
        ):

            tables[
                "insight_evidence"
            ].append(
                {
                    "study_id": (
                        study_id
                    ),

                    "insight_key": (
                        insight_key
                    ),

                    "insight_type": (
                        insight_type
                    ),

                    "insight_id": (
                        insight_id
                    ),

                    "evidence_key": (
                        self._evidence_key(
                            study_id=study_id,
                            evidence_id=(
                                evidence_id
                            ),
                        )
                    ),

                    "evidence_id": (
                        evidence_id
                    ),
                }
            )

    # =====================================================
    # Segments
    # =====================================================

    def _add_segments(
        self,
        tables: dict[
            str,
            list[dict[str, Any]],
        ],
        report: StudyReportAnalysis,
        study_id: str,
    ) -> None:

        for segment_index, segment in enumerate(
            report.segment_differences,
            start=1,
        ):

            segment_id = (
                f"SEG{segment_index:03d}"
            )

            segment_key = (
                f"{study_id}::{segment_id}"
            )

            tables["segments"].append(
                {
                    "study_id": (
                        study_id
                    ),

                    "segment_key": (
                        segment_key
                    ),

                    "segment_id": (
                        segment_id
                    ),

                    "segment_name": (
                        segment.segment_name
                    ),

                    "segment_description": (
                        segment
                        .segment_description
                    ),

                    "participant_count": (
                        segment
                        .participant_count
                    ),

                    "key_difference": (
                        segment
                        .key_difference
                    ),
                }
            )

            for group_index, group in enumerate(
                segment.groups,
                start=1,
            ):

                group_id = (
                    f"{segment_id}_G"
                    f"{group_index:02d}"
                )

                group_key = (
                    f"{study_id}::{group_id}"
                )

                tables[
                    "segment_groups"
                ].append(
                    {
                        "study_id": (
                            study_id
                        ),

                        "segment_key": (
                            segment_key
                        ),

                        "segment_id": (
                            segment_id
                        ),

                        "group_key": (
                            group_key
                        ),

                        "group_id": (
                            group_id
                        ),

                        "group_name": (
                            group.group_name
                        ),

                        "group_description": (
                            group
                            .group_description
                        ),

                        "participant_count": (
                            group
                            .participant_count
                        ),
                    }
                )

                # -------------------------------------
                # Segment Group ↔ Participant
                # -------------------------------------

                for participant_id in (
                    group.participant_ids
                ):

                    tables[
                        "segment_group_participants"
                    ].append(
                        {
                            "study_id": (
                                study_id
                            ),

                            "segment_key": (
                                segment_key
                            ),

                            "group_key": (
                                group_key
                            ),

                            "participant_key": (
                                self._participant_key(
                                    study_id=(
                                        study_id
                                    ),
                                    participant_id=(
                                        participant_id
                                    ),
                                )
                            ),

                            "participant_id": (
                                participant_id
                            ),
                        }
                    )

                # -------------------------------------
                # Segment Group ↔ Evidence
                # -------------------------------------

                for evidence_id in (
                    group.evidence_ids
                ):

                    tables[
                        "segment_group_evidence"
                    ].append(
                        {
                            "study_id": (
                                study_id
                            ),

                            "segment_key": (
                                segment_key
                            ),

                            "group_key": (
                                group_key
                            ),

                            "evidence_key": (
                                self._evidence_key(
                                    study_id=(
                                        study_id
                                    ),
                                    evidence_id=(
                                        evidence_id
                                    ),
                                )
                            ),

                            "evidence_id": (
                                evidence_id
                            ),
                        }
                    )

    # =====================================================
    # Evidence
    # =====================================================

    def _add_evidence(
        self,
        tables: dict[
            str,
            list[dict[str, Any]],
        ],
        report: StudyReportAnalysis,
        study_id: str,
    ) -> None:

        for item in report.evidence:

            tables["evidence"].append(
                {
                    "study_id": (
                        study_id
                    ),

                    "evidence_key": (
                        self._evidence_key(
                            study_id=study_id,
                            evidence_id=(
                                item.evidence_id
                            ),
                        )
                    ),

                    "evidence_id": (
                        item.evidence_id
                    ),

                    "participant_key": (
                        self._participant_key(
                            study_id=study_id,
                            participant_id=(
                                item.participant_id
                            ),
                        )
                    ),

                    "participant_id": (
                        item.participant_id
                    ),

                    "session_id": (
                        item.session_id
                    ),

                    "question_id": (
                        item.question_id
                    ),

                    "quote": (
                        item.quote
                    ),
                }
            )

    # =====================================================
    # Helpers
    # =====================================================

    def _participant_key(
        self,
        study_id: str,
        participant_id: str,
    ) -> str:

        return (
            f"{study_id}::"
            f"{participant_id}"
        )

    def _evidence_key(
        self,
        study_id: str,
        evidence_id: str,
    ) -> str:

        return (
            f"{study_id}::"
            f"{evidence_id}"
        )

    def _insight_key(
        self,
        study_id: str,
        insight_type: str,
        insight_id: str,
    ) -> str:

        return (
            f"{study_id}::"
            f"{insight_type}::"
            f"{insight_id}"
        )

    def _safe_ratio(
        self,
        numerator: int,
        denominator: int,
    ) -> float | None:

        if denominator <= 0:
            return None

        return round(
            numerator / denominator,
            4,
        )

    def _join_text(
        self,
        values: list[str],
    ) -> str:

        return " | ".join(
            value.strip()
            for value in values
            if value.strip()
        )


# =========================================================
# Singleton
# =========================================================

_bi_transformer: (
    StudyReportBITransformer | None
) = None


def get_study_report_bi_transformer(
) -> StudyReportBITransformer:

    global _bi_transformer

    if _bi_transformer is None:
        _bi_transformer = (
            StudyReportBITransformer()
        )

    return _bi_transformer