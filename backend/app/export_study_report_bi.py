from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import xlsxwriter

from app.schemas.study_report import StudyReportAnalysis
from app.services.report.bi_transformer import (
    get_study_report_bi_transformer,
)


# =========================================================
# 경로
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

REPORT_DIR = (
    BASE_DIR
    / "ai-interview-report"
)

INPUT_PATH = (
    REPORT_DIR
    / "study_report.json"
)

OUTPUT_PATH = (
    REPORT_DIR
    / "study_report_powerbi.xlsx"
)


# =========================================================
# Excel Sheet 이름
# =========================================================

SHEET_NAMES = {
    "studies": "Studies",

    "participants": "Participants",

    "coverage": "Coverage",

    "insights": "Insights",

    "insight_participants": (
        "InsightParticipants"
    ),

    "insight_evidence": (
        "InsightEvidence"
    ),

    "segments": "Segments",

    "segment_groups": (
        "SegmentGroups"
    ),

    "segment_group_participants": (
        "SegmentParticipants"
    ),

    "segment_group_evidence": (
        "SegmentEvidence"
    ),

    "evidence": "Evidence",
}


# =========================================================
# 각 Sheet 컬럼 순서
#
# 데이터가 0건이어도 컬럼 구조는 유지한다.
# =========================================================

TABLE_COLUMNS = {
    "studies": [
        "study_id",
        "research_title",
        "research_purpose",
        "participant_count",
        "completed_session_count",
        "question_count",
        "overall_coverage",
        "core_insight",
        "executive_summary",
    ],

    "participants": [
        "study_id",
        "participant_key",
        "participant_id",
    ],

    "coverage": [
        "study_id",
        "coverage_id",
        "question_id",
        "question",
        "coverage",
        "participant_count",
        "covered_participant_count",
        "coverage_rate",
        "reason",
        "missing_information",
    ],

    "insights": [
        "study_id",
        "insight_key",
        "insight_type",
        "insight_id",
        "title",
        "description",
        "participant_count",
        "strength",
        "priority",
        "source_type",
        "expected_value",
    ],

    "insight_participants": [
        "study_id",
        "insight_key",
        "insight_type",
        "insight_id",
        "participant_key",
        "participant_id",
    ],

    "insight_evidence": [
        "study_id",
        "insight_key",
        "insight_type",
        "insight_id",
        "evidence_key",
        "evidence_id",
    ],

    "segments": [
        "study_id",
        "segment_key",
        "segment_id",
        "segment_name",
        "segment_description",
        "participant_count",
        "key_difference",
    ],

    "segment_groups": [
        "study_id",
        "segment_key",
        "segment_id",
        "group_key",
        "group_id",
        "group_name",
        "group_description",
        "participant_count",
    ],

    "segment_group_participants": [
        "study_id",
        "segment_key",
        "group_key",
        "participant_key",
        "participant_id",
    ],

    "segment_group_evidence": [
        "study_id",
        "segment_key",
        "group_key",
        "evidence_key",
        "evidence_id",
    ],

    "evidence": [
        "study_id",
        "evidence_key",
        "evidence_id",
        "participant_key",
        "participant_id",
        "session_id",
        "question_id",
        "quote",
    ],
}


# =========================================================
# Excel Table 이름
#
# Power BI에서는 Sheet보다
# 이 tblXXX Table을 가져온다.
# =========================================================

EXCEL_TABLE_NAMES = {
    "studies": (
        "tblStudies"
    ),

    "participants": (
        "tblParticipants"
    ),

    "coverage": (
        "tblCoverage"
    ),

    "insights": (
        "tblInsights"
    ),

    "insight_participants": (
        "tblInsightParticipants"
    ),

    "insight_evidence": (
        "tblInsightEvidence"
    ),

    "segments": (
        "tblSegments"
    ),

    "segment_groups": (
        "tblSegmentGroups"
    ),

    "segment_group_participants": (
        "tblSegmentParticipants"
    ),

    "segment_group_evidence": (
        "tblSegmentEvidence"
    ),

    "evidence": (
        "tblEvidence"
    ),
}


# =========================================================
# Study Report JSON 읽기
# =========================================================

def load_study_report(
) -> StudyReportAnalysis:

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            "study_report.json 파일을 "
            "찾을 수 없습니다.\n"
            f"경로: {INPUT_PATH}"
        )

    with INPUT_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:

        raw_data = json.load(
            file
        )

    return (
        StudyReportAnalysis
        .model_validate(
            raw_data
        )
    )


# =========================================================
# Excel 셀 값 변환
# =========================================================

def normalize_cell_value(
    value: Any,
) -> Any:

    if value is None:
        return ""

    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    ):
        return value

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        return " | ".join(
            str(item)
            for item in value
        )

    if isinstance(
        value,
        dict,
    ):
        return json.dumps(
            value,
            ensure_ascii=False,
        )

    return str(
        value
    )


# =========================================================
# Excel 컬럼 너비
# =========================================================

def calculate_column_width(
    column_name: str,
    rows: list[
        dict[str, Any]
    ],
) -> int:

    max_length = len(
        column_name
    )

    # 너무 많은 Row 전체를 돌 필요는 없음
    for row in rows[:200]:

        value = (
            normalize_cell_value(
                row.get(
                    column_name
                )
            )
        )

        text = str(
            value
        )

        if (
            len(text)
            > max_length
        ):
            max_length = (
                len(text)
            )

    long_text_columns = {
        "research_purpose",
        "core_insight",
        "executive_summary",
        "question",
        "reason",
        "missing_information",
        "title",
        "description",
        "expected_value",
        "segment_name",
        "segment_description",
        "group_name",
        "group_description",
        "key_difference",
        "quote",
    }

    if (
        column_name
        in long_text_columns
    ):
        return min(
            max(
                max_length + 2,
                20,
            ),
            55,
        )

    return min(
        max(
            max_length + 2,
            10,
        ),
        40,
    )


# =========================================================
# Excel Sheet 작성
# =========================================================

def write_table_sheet(
    workbook: (
        xlsxwriter.Workbook
    ),
    table_key: str,
    rows: list[
        dict[str, Any]
    ],
) -> None:

    sheet_name = (
        SHEET_NAMES[
            table_key
        ]
    )

    columns = (
        TABLE_COLUMNS[
            table_key
        ]
    )

    table_name = (
        EXCEL_TABLE_NAMES[
            table_key
        ]
    )

    worksheet = (
        workbook
        .add_worksheet(
            sheet_name
        )
    )

    # =====================================================
    # 기본 화면 설정
    # =====================================================

    worksheet.freeze_panes(
        1,
        0,
    )

    worksheet.hide_gridlines(
        2
    )

    # =====================================================
    # Format
    # =====================================================

    header_format = (
        workbook.add_format(
            {
                "bold": True,
                "font_color": (
                    "#FFFFFF"
                ),
                "bg_color": (
                    "#1F4E78"
                ),
                "border": 1,
                "align": (
                    "center"
                ),
                "valign": (
                    "vcenter"
                ),
                "text_wrap": True,
            }
        )
    )

    text_format = (
        workbook.add_format(
            {
                "valign": (
                    "top"
                ),
                "text_wrap": True,
            }
        )
    )

    center_format = (
        workbook.add_format(
            {
                "align": (
                    "center"
                ),
                "valign": (
                    "top"
                ),
            }
        )
    )

    integer_format = (
        workbook.add_format(
            {
                "num_format": (
                    "0"
                ),
                "align": (
                    "center"
                ),
                "valign": (
                    "top"
                ),
            }
        )
    )

    ratio_format = (
        workbook.add_format(
            {
                "num_format": (
                    "0.0%"
                ),
                "align": (
                    "center"
                ),
                "valign": (
                    "top"
                ),
            }
        )
    )

    # =====================================================
    # Header
    # =====================================================

    for (
        column_index,
        column_name,
    ) in enumerate(
        columns
    ):

        worksheet.write(
            0,
            column_index,
            column_name,
            header_format,
        )

    # =====================================================
    # 타입별 컬럼
    # =====================================================

    integer_columns = {
        "participant_count",
        "completed_session_count",
        "question_count",
        "covered_participant_count",
    }

    center_columns = {
        "study_id",

        "participant_key",
        "participant_id",

        "coverage_id",
        "question_id",
        "coverage",

        "insight_key",
        "insight_type",
        "insight_id",

        "strength",
        "priority",
        "source_type",

        "segment_key",
        "segment_id",

        "group_key",
        "group_id",

        "evidence_key",
        "evidence_id",

        "session_id",
    }

    # =====================================================
    # Data
    # =====================================================

    for row_index, row in enumerate(
        rows,
        start=1,
    ):

        for (
            column_index,
            column_name,
        ) in enumerate(
            columns
        ):

            value = (
                normalize_cell_value(
                    row.get(
                        column_name
                    )
                )
            )

            # ---------------------------------------------
            # Percentage
            # ---------------------------------------------

            if (
                column_name
                == "coverage_rate"
            ):

                if value == "":

                    worksheet.write_blank(
                        row_index,
                        column_index,
                        None,
                        ratio_format,
                    )

                else:

                    worksheet.write_number(
                        row_index,
                        column_index,
                        float(
                            value
                        ),
                        ratio_format,
                    )

            # ---------------------------------------------
            # Integer
            # ---------------------------------------------

            elif (
                column_name
                in integer_columns
                and value != ""
            ):

                worksheet.write_number(
                    row_index,
                    column_index,
                    int(
                        value
                    ),
                    integer_format,
                )

            # ---------------------------------------------
            # Key / ID
            # ---------------------------------------------

            elif (
                column_name
                in center_columns
            ):

                worksheet.write(
                    row_index,
                    column_index,
                    value,
                    center_format,
                )

            # ---------------------------------------------
            # 일반 Text
            # ---------------------------------------------

            else:

                worksheet.write(
                    row_index,
                    column_index,
                    value,
                    text_format,
                )

    # =====================================================
    # Excel Table 생성
    #
    # Row가 0개인 테이블도 Header 구조는 생성한다.
    # =====================================================

    last_row = max(
        len(rows),
        1,
    )

    last_column = (
        len(columns)
        - 1
    )

    worksheet.add_table(
        0,
        0,
        last_row,
        last_column,
        {
            "name": (
                table_name
            ),

            "style": (
                "Table Style Medium 2"
            ),

            "columns": [
                {
                    "header": (
                        column_name
                    )
                }
                for column_name
                in columns
            ],
        },
    )

    # =====================================================
    # Column Width
    # =====================================================

    for (
        column_index,
        column_name,
    ) in enumerate(
        columns
    ):

        width = (
            calculate_column_width(
                column_name=(
                    column_name
                ),
                rows=rows,
            )
        )

        worksheet.set_column(
            column_index,
            column_index,
            width,
        )

    worksheet.set_row(
        0,
        28,
    )


# =========================================================
# Power BI Guide
# =========================================================

def write_readme_sheet(
    workbook: (
        xlsxwriter.Workbook
    ),
) -> None:

    worksheet = (
        workbook
        .add_worksheet(
            "PowerBI_Guide"
        )
    )

    worksheet.hide_gridlines(
        2
    )

    title_format = (
        workbook.add_format(
            {
                "bold": True,
                "font_size": 18,
                "font_color": (
                    "#1F4E78"
                ),
            }
        )
    )

    section_format = (
        workbook.add_format(
            {
                "bold": True,
                "font_size": 12,
                "font_color": (
                    "#FFFFFF"
                ),
                "bg_color": (
                    "#1F4E78"
                ),
            }
        )
    )

    text_format = (
        workbook.add_format(
            {
                "text_wrap": True,
                "valign": (
                    "top"
                ),
            }
        )
    )

    code_format = (
        workbook.add_format(
            {
                "font_name": (
                    "Consolas"
                ),
                "font_size": 10,
                "text_wrap": True,
                "valign": (
                    "top"
                ),
                "bg_color": (
                    "#F2F2F2"
                ),
            }
        )
    )

    # =====================================================
    # 제목
    # =====================================================

    worksheet.write(
        "A1",
        (
            "AI Interview Study Report "
            "- Power BI Guide"
        ),
        title_format,
    )

    # =====================================================
    # 목적
    # =====================================================

    worksheet.write(
        "A3",
        "목적",
        section_format,
    )

    worksheet.write(
        "A4",
        (
            "특정 조사 주제에 종속되지 않는 "
            "범용 Study Report 데이터 모델입니다. "
            "참여자 수, 질문 수, 조사 주제, "
            "Insight 개수가 달라져도 동일한 "
            "Power BI 구조를 사용할 수 있습니다."
        ),
        text_format,
    )

    # =====================================================
    # Key 규칙
    # =====================================================

    worksheet.write(
        "A6",
        "중요 고유키",
        section_format,
    )

    key_rules = [
        (
            "participant_key",
            (
                "study_id + participant_id. "
                "서로 다른 Study의 P01 충돌 방지."
            ),
        ),
        (
            "evidence_key",
            (
                "study_id + evidence_id. "
                "서로 다른 Study의 P01_E001 충돌 방지."
            ),
        ),
        (
            "insight_key",
            (
                "study_id + insight_type + insight_id."
            ),
        ),
        (
            "segment_key",
            (
                "study_id + segment_id."
            ),
        ),
        (
            "group_key",
            (
                "study_id + group_id."
            ),
        ),
    ]

    row = 6

    for (
        key_name,
        explanation,
    ) in key_rules:

        worksheet.write(
            row,
            0,
            key_name,
            code_format,
        )

        worksheet.write(
            row,
            1,
            explanation,
            text_format,
        )

        row += 1

    # =====================================================
    # 테이블 설명
    # =====================================================

    row += 2

    worksheet.write(
        row,
        0,
        "주요 Table",
        section_format,
    )

    row += 1

    table_descriptions = [
        (
            "tblStudies",
            (
                "Study 1건당 1행. 조사 제목, 목적, "
                "참여자 수, Executive Summary."
            ),
        ),

        (
            "tblParticipants",
            (
                "Study별 인터뷰 참여자. "
                "participant_key를 고유키로 사용."
            ),
        ),

        (
            "tblCoverage",
            (
                "질문별 Research Coverage."
            ),
        ),

        (
            "tblInsights",
            (
                "Executive Takeaway / Finding / Theme / "
                "Driver / Pain Point / Need / Opportunity / "
                "Research Gap을 범용 구조로 저장."
            ),
        ),

        (
            "tblInsightParticipants",
            (
                "Insight와 이를 지지한 Participant의 "
                "연결 데이터."
            ),
        ),

        (
            "tblInsightEvidence",
            (
                "Insight와 실제 Evidence의 연결 데이터."
            ),
        ),

        (
            "tblEvidence",
            (
                "실제 인터뷰 원문 Evidence. "
                "evidence_key를 고유키로 사용."
            ),
        ),

        (
            "tblSegments",
            (
                "검증을 통과한 Segment Difference."
            ),
        ),

        (
            "tblSegmentGroups",
            (
                "각 Segment 내부 비교 그룹."
            ),
        ),

        (
            "tblSegmentParticipants",
            (
                "Segment Group과 Participant 연결."
            ),
        ),

        (
            "tblSegmentEvidence",
            (
                "Segment Group과 Evidence 연결."
            ),
        ),
    ]

    for (
        table_name,
        description,
    ) in table_descriptions:

        worksheet.write(
            row,
            0,
            table_name,
            code_format,
        )

        worksheet.write(
            row,
            1,
            description,
            text_format,
        )

        row += 1

    # =====================================================
    # 권장 기본 관계
    #
    # 일부 Bridge의 보조 관계는
    # Power BI에서 필요에 따라 추가한다.
    #
    # 여러 경로를 무조건 활성화하면
    # Ambiguous Relationship이 생길 수 있으므로
    # 기본 관계만 적는다.
    # =====================================================

    row += 2

    worksheet.write(
        row,
        0,
        "권장 기본 Power BI 관계",
        section_format,
    )

    row += 1

    relationships = [
        (
            "tblStudies[study_id]",
            "1 → *",
            "tblCoverage[study_id]",
        ),

        (
            "tblStudies[study_id]",
            "1 → *",
            "tblInsights[study_id]",
        ),

        (
            "tblStudies[study_id]",
            "1 → *",
            "tblParticipants[study_id]",
        ),

        (
            "tblStudies[study_id]",
            "1 → *",
            "tblSegments[study_id]",
        ),

        (
            "tblParticipants[participant_key]",
            "1 → *",
            "tblEvidence[participant_key]",
        ),

        (
            "tblInsights[insight_key]",
            "1 → *",
            (
                "tblInsightParticipants"
                "[insight_key]"
            ),
        ),

        (
            "tblInsights[insight_key]",
            "1 → *",
            (
                "tblInsightEvidence"
                "[insight_key]"
            ),
        ),

        (
            "tblSegments[segment_key]",
            "1 → *",
            (
                "tblSegmentGroups"
                "[segment_key]"
            ),
        ),

        (
            "tblSegmentGroups[group_key]",
            "1 → *",
            (
                "tblSegmentParticipants"
                "[group_key]"
            ),
        ),

        (
            "tblSegmentGroups[group_key]",
            "1 → *",
            (
                "tblSegmentEvidence"
                "[group_key]"
            ),
        ),
    ]

    for (
        left,
        relation,
        right,
    ) in relationships:

        worksheet.write(
            row,
            0,
            left,
            code_format,
        )

        worksheet.write(
            row,
            1,
            relation,
            text_format,
        )

        worksheet.write(
            row,
            2,
            right,
            code_format,
        )

        row += 1

    # =====================================================
    # 추가 연결키 설명
    # =====================================================

    row += 2

    worksheet.write(
        row,
        0,
        "추가 Bridge Key",
        section_format,
    )

    row += 1

    extra_keys = [
        (
            (
                "tblInsightParticipants"
                "[participant_key]"
            ),
            (
                "tblParticipants"
                "[participant_key]"
            ),
        ),

        (
            (
                "tblInsightEvidence"
                "[evidence_key]"
            ),
            (
                "tblEvidence"
                "[evidence_key]"
            ),
        ),

        (
            (
                "tblSegmentParticipants"
                "[participant_key]"
            ),
            (
                "tblParticipants"
                "[participant_key]"
            ),
        ),

        (
            (
                "tblSegmentEvidence"
                "[evidence_key]"
            ),
            (
                "tblEvidence"
                "[evidence_key]"
            ),
        ),
    ]

    for (
        left,
        right,
    ) in extra_keys:

        worksheet.write(
            row,
            0,
            left,
            code_format,
        )

        worksheet.write(
            row,
            1,
            "↔",
            text_format,
        )

        worksheet.write(
            row,
            2,
            right,
            code_format,
        )

        row += 1

    # =====================================================
    # 추천 Dashboard
    # =====================================================

    row += 2

    worksheet.write(
        row,
        0,
        "추천 Dashboard",
        section_format,
    )

    row += 1

    visuals = [
        "Card: 전체 참여자 수",

        "Card: 전체 질문 수",

        (
            "Bar: 질문별 "
            "Research Coverage"
        ),

        (
            "Bar: Key Finding별 "
            "participant_count"
        ),

        (
            "Bar: Pain Point별 "
            "participant_count"
        ),

        (
            "Bar: Key Driver별 "
            "participant_count"
        ),

        (
            "Bar: Need별 "
            "participant_count"
        ),

        (
            "Bar: Opportunity별 "
            "participant_count"
        ),

        (
            "Table: Insight title / "
            "participant_count / "
            "priority / strength"
        ),

        (
            "Evidence Drill-through: "
            "선택한 Insight의 실제 인터뷰 발언 확인"
        ),

        (
            "Segment 비교: "
            "Group별 participant_count 및 Evidence"
        ),
    ]

    for visual in visuals:

        worksheet.write(
            row,
            0,
            f"• {visual}",
            text_format,
        )

        row += 1

    worksheet.set_column(
        "A:A",
        42,
    )

    worksheet.set_column(
        "B:B",
        60,
    )

    worksheet.set_column(
        "C:C",
        50,
    )


# =========================================================
# Excel 생성
# =========================================================

def export_powerbi_excel(
    tables: dict[
        str,
        list[dict[str, Any]],
    ],
    target: Any = None,
) -> None:

    out_target = target if target is not None else OUTPUT_PATH
    if isinstance(out_target, (str, Path)):
        Path(out_target).parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    workbook = (
        xlsxwriter.Workbook(
            out_target,
            {"in_memory": True} if hasattr(out_target, "write") else {},
        )
    )

    try:

        write_readme_sheet(
            workbook
        )

        table_order = (
            "studies",
            "participants",
            "coverage",
            "insights",
            "insight_participants",
            "insight_evidence",
            "segments",
            "segment_groups",
            "segment_group_participants",
            "segment_group_evidence",
            "evidence",
        )

        for table_key in (
            table_order
        ):

            write_table_sheet(
                workbook=(
                    workbook
                ),
                table_key=(
                    table_key
                ),
                rows=tables[
                    table_key
                ],
            )

    finally:

        workbook.close()


# =========================================================
# 변환 결과 출력
# =========================================================

def print_table_summary(
    tables: dict[
        str,
        list[dict[str, Any]],
    ],
) -> None:

    print()

    print(
        "========================================"
    )

    print(
        "Power BI 데이터 변환 결과"
    )

    print(
        "========================================"
    )

    for (
        table_name,
        rows,
    ) in tables.items():

        print(
            f"{table_name}: "
            f"{len(rows)} rows"
        )


# =========================================================
# Main
# =========================================================

def main() -> None:

    print()

    print(
        "========================================"
    )

    print(
        "Study Report → Power BI Excel"
    )

    print(
        "========================================"
    )

    # -----------------------------------------------------
    # Study Report
    # -----------------------------------------------------

    report = (
        load_study_report()
    )

    # -----------------------------------------------------
    # BI Transformer
    # -----------------------------------------------------

    transformer = (
        get_study_report_bi_transformer()
    )

    tables = (
        transformer.transform(
            report
        )
    )

    # -----------------------------------------------------
    # Row 수 확인
    # -----------------------------------------------------

    print_table_summary(
        tables
    )

    # -----------------------------------------------------
    # Excel 생성
    # -----------------------------------------------------

    export_powerbi_excel(
        tables
    )

    print()

    print(
        "========================================"
    )

    print(
        "Power BI Excel 생성 완료"
    )

    print(
        "========================================"
    )

    print(
        f"생성 파일: "
        f"{OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()