from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.schemas.study import ResearchStudy
from app.services.report.study_analyzer import (
    get_study_report_analyzer,
)


# =========================================================
# 환경 변수
# =========================================================

load_dotenv()


# =========================================================
# 경로
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

REPORT_DIR = BASE_DIR / "ai-interview-report"

DUMMY_DATA_PATH = (
    REPORT_DIR
    / "dummy_ai_interviews_12.json"
)

OUTPUT_PATH = (
    REPORT_DIR
    / "study_report.json"
)


# =========================================================
# 현재 테스트용 Research Study
#
# 주의:
# - 이 질문지는 테스트용이다.
# - 실제 서비스에서는 ResearchStudy에 저장된
#   research_purpose / question_script를 사용한다.
# - StudyReportAnalyzer 자체에는 이 질문이 고정되지 않는다.
# =========================================================

TEST_RESEARCH_TITLE = (
    "[TEST] OpenAI Codex vs Claude Code "
    "사용자 선호도 리서치"
)

TEST_RESEARCH_PURPOSE = """
OpenAI Codex 기반 모델의 뛰어난 순수 성능에도 불구하고,
개발자들이 터미널 기반 작업에서 Claude Code를 더 선호하거나
스위칭하는 결정적 요인인 UX, 워크플로우,
컨텍스트 관리 방식을 파악하고
OpenAI가 극복해야 할 제품적·전략적 Gap을 도출한다.
""".strip()


TEST_QUESTION_SCRIPT = """
1. 현재 터미널이나 개발 환경에서 주로 어떤 AI 툴 조합을 사용하고 계시나요?
   - 평소 일상적인 코딩과 복잡한 리팩토링/디버깅 시 사용하는 툴이 다른가요?

2. '모델 성능은 OpenAI가 최고인데, 터미널 작업은 결국 Claude Code를 켜게 된다'는 이야기에 공감하시나요? 공감하신다면 결정적인 이유가 무엇인가요?
   - 터미널 환경에서 대화의 흐름이나 멀티스텝 작업 처리가 어떻게 다르게 느껴지나요?
   - 대규모 코드베이스를 읽고 수정하는 과정에서 의도를 더 잘 파악한다고 느끼는 구체적인 순간이 있나요?

3. OpenAI 모델이나 관련 툴을 쓰면서 흐름이 끊기거나 답답하다고 느꼈던 경험은 무엇인가요?
   - 불필요하게 개입하거나 수동으로 수정해야 했던 번거로움이 있었나요?
   - 속도, 비용, 에이전트 자율성 중 어떤 요소가 가장 아쉬웠나요?

4. 만약 내일 당장 OpenAI가 터미널 기반 개발 경험을 혁신적으로 바꿀 단 하나의 기능을 내놓는다면 어떤 모습이어야 할까요?
""".strip()


# =========================================================
# 테스트 인터뷰 질문 순서
#
# 현재 dummy 데이터 생성 시 사용한 질문 순서와 동일하다.
# 이것 역시 테스트 파일에서만 사용된다.
# =========================================================

TEST_QUESTION_ORDER = [
    "q1",
    "q1_probe1",
    "q2",
    "q2_probe1",
    "q2_probe2",
    "q3",
    "q3_probe1",
    "q3_probe2",
    "q4",
]


# =========================================================
# JSON 읽기
# =========================================================

def load_dummy_dataset() -> dict[str, Any]:
    if not DUMMY_DATA_PATH.exists():
        raise FileNotFoundError(
            "더미 인터뷰 파일을 찾을 수 없습니다.\n"
            f"경로: {DUMMY_DATA_PATH}"
        )

    with DUMMY_DATA_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


# =========================================================
# ResearchStudy 생성
#
# 테스트이므로 직접 생성한다.
#
# 실제 서비스:
# 기업이 Study 생성
# → DB에 ResearchStudy 저장
# → 해당 Study를 읽어서 사용
# =========================================================

def build_test_study() -> ResearchStudy:
    return ResearchStudy(
        title=TEST_RESEARCH_TITLE,
        research_purpose=TEST_RESEARCH_PURPOSE,
        question_script=TEST_QUESTION_SCRIPT,
    )


# =========================================================
# Raw Dummy Interview
# →
# Study Analyzer가 읽을 Participant Report 형태로 변환
#
# 여기서는 Study Analyzer 자체를 먼저 테스트하기 위해
# 개별 AI 리포트를 다시 12번 생성하지 않는다.
#
# 대신 각 인터뷰의 실제 synthetic 답변을
# Evidence 형태로 전달한다.
# =========================================================

def build_participant_reports(
    dataset: dict[str, Any],
) -> list[dict[str, Any]]:

    interviews = dataset.get(
        "interviews",
        [],
    )

    if not interviews:
        raise ValueError(
            "dummy 데이터에 interviews가 없습니다."
        )

    participant_reports: list[
        dict[str, Any]
    ] = []

    for participant_index, interview in enumerate(
        interviews,
        start=1,
    ):
        session = interview.get(
            "session",
            {},
        )

        profile = interview.get(
            "participant_profile",
            {},
        )

        transcript = interview.get(
            "transcript",
            [],
        )

        participant_id = (
            session.get("participant_id")
            or profile.get("participant_id")
            or f"P{participant_index:02d}"
        )

        session_id = (
            session.get("id")
            or f"ses_test_{participant_id.lower()}"
        )

        evidence_items: list[
            dict[str, Any]
        ] = []

        interviewee_turns = [
            turn
            for turn in transcript
            if turn.get("speaker") == "interviewee"
        ]

        for evidence_number, turn in enumerate(
            interviewee_turns,
            start=1,
        ):
            evidence_id = (
                f"{participant_id}_E"
                f"{evidence_number:03d}"
            )

            question_id = None

            order_index = (
                evidence_number - 1
            )

            if order_index < len(
                TEST_QUESTION_ORDER
            ):
                question_id = (
                    TEST_QUESTION_ORDER[
                        order_index
                    ]
                )

            evidence_items.append(
                {
                    "evidence_id": evidence_id,
                    "turn_index": turn.get(
                        "index",
                        evidence_number,
                    ),
                    "speaker": "interviewee",
                    "quote": turn.get(
                        "text",
                        "",
                    ),
                    "created_at": turn.get(
                        "created_at",
                    ),
                    "question_id": question_id,
                }
            )

        first_evidence_ids = []

        if evidence_items:
            first_evidence_ids = [
                evidence_items[0][
                    "evidence_id"
                ]
            ]

        role = profile.get(
            "role",
            "미상",
        )

        main_tool = profile.get(
            "main_tool",
            "미상",
        )

        overall_preference = profile.get(
            "overall_preference",
            "미상",
        )

        current_behavior = profile.get(
            "current_behavior",
            "",
        )

        primary_driver = profile.get(
            "primary_driver",
            "",
        )

        top_pain_point = profile.get(
            "top_pain_point",
            "",
        )

        top_feature = profile.get(
            "top_feature",
            "",
        )

        participant_report = {
            "participant_id": participant_id,
            "session_id": session_id,

            "data": {
                "participant_context": {
                    "summary": (
                        f"{role}. "
                        f"주요 사용 툴은 {main_tool}. "
                        f"현재 테스트 데이터상 "
                        f"전반적 선호는 "
                        f"{overall_preference}."
                    ),
                    "attributes": [
                        {
                            "name": "직무",
                            "value": role,
                            "evidence_ids": (
                                first_evidence_ids
                            ),
                        },
                        {
                            "name": "주요 사용 툴",
                            "value": main_tool,
                            "evidence_ids": (
                                first_evidence_ids
                            ),
                        },
                    ],
                },

                "executive_summary": {
                    "core_insight": (
                        current_behavior
                    ),
                    "summary": (
                        f"주요 판단 요인: "
                        f"{primary_driver}. "
                        f"주요 불편: "
                        f"{top_pain_point}. "
                        f"요구 기능: "
                        f"{top_feature}."
                    ),
                    "key_takeaways": [],
                },

                "research_coverage": {},
                "slot_coverage": {},

                "key_findings": [],
                "themes": [],
                "key_drivers": [],

                "needs_and_pain_points": [],

                "decision_dynamics": None,

                "opportunities": [],

                "researcher_attention": [],

                "evidence": evidence_items,
            },
        }

        participant_reports.append(
            participant_report
        )

    return participant_reports


# =========================================================
# Study Report 저장
# =========================================================

def save_study_report(
    report: Any,
) -> None:

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report.model_dump(
                mode="json"
            ),
            file,
            ensure_ascii=False,
            indent=2,
        )


# =========================================================
# Main
# =========================================================

async def main() -> None:

    print()
    print(
        "========================================"
    )
    print(
        "Study 종합 리포트 테스트"
    )
    print(
        "========================================"
    )

    dataset = load_dummy_dataset()

    participant_reports = (
        build_participant_reports(
            dataset
        )
    )

    study = build_test_study()

    print(
        f"Study ID: {study.id}"
    )

    print(
        "테스트 참여자 수: "
        f"{len(participant_reports)}"
    )

    evidence_count = sum(
        len(
            report["data"]["evidence"]
        )
        for report
        in participant_reports
    )

    print(
        "전체 Evidence 수: "
        f"{evidence_count}"
    )

    print()
    print(
        "AI Study 종합 분석 준비 완료"
    )

    analyzer = (
        get_study_report_analyzer()
    )

    result = await analyzer.analyze(
        study=study,
        participant_reports=(
            participant_reports
        ),
    )

    save_study_report(
        result
    )

    print()
    print(
        "========================================"
    )
    print(
        "Study 종합 리포트 생성 완료"
    )
    print(
        "========================================"
    )

    print(
        f"참여자 수: "
        f"{result.overview.participant_count}"
    )

    print(
        f"Key Findings: "
        f"{len(result.key_findings)}"
    )

    print(
        f"Themes: "
        f"{len(result.themes)}"
    )

    print(
        f"Drivers: "
        f"{len(result.key_drivers)}"
    )

    print(
        f"Pain Points: "
        f"{len(result.pain_points)}"
    )

    print(
        f"Needs: "
        f"{len(result.needs)}"
    )

    print(
        f"Segments: "
        f"{len(result.segment_differences)}"
    )

    print(
        f"Opportunities: "
        f"{len(result.opportunities)}"
    )

    print()
    print(
        f"생성 파일: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    asyncio.run(
        main()
    )