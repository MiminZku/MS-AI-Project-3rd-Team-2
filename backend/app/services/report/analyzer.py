from __future__ import annotations

import json
import logging
from typing import Any, Protocol

from app.core.config import get_settings
from app.schemas.report_analysis import IndividualInterviewAnalysis
from app.schemas.session import Instruction, Session, Turn

logger = logging.getLogger(__name__)


# =========================================================
# 이번 리서치에서 반드시 확보해야 하는 Information Slot
# =========================================================

SLOT_DEFINITIONS = [
    {
        "slot_id": "current_tool_stack",
        "question_id": "q1",
        "slot_name": "현재 사용 중인 AI 툴 조합",
    },
    {
        "slot_id": "task_based_tool_choice",
        "question_id": "q1",
        "slot_name": "작업 유형별 툴 선택 기준",
    },
    {
        "slot_id": "preference_reason",
        "question_id": "q2",
        "slot_name": "Claude Code 또는 Codex 선호 이유",
    },
    {
        "slot_id": "workflow_continuity",
        "question_id": "q2",
        "slot_name": "작업 흐름의 연속성",
    },
    {
        "slot_id": "context_management",
        "question_id": "q2",
        "slot_name": "컨텍스트 관리 경험",
    },
    {
        "slot_id": "agent_autonomy",
        "question_id": "q2",
        "slot_name": "에이전트 자율성",
    },
    {
        "slot_id": "concrete_example",
        "question_id": "q2",
        "slot_name": "구체적인 실제 사용 사례",
    },
    {
        "slot_id": "openai_pain_point",
        "question_id": "q3",
        "slot_name": "OpenAI 도구의 핵심 Pain Point",
    },
    {
        "slot_id": "manual_intervention",
        "question_id": "q3",
        "slot_name": "수동 개입 및 반복 컨펌 부담",
    },
    {
        "slot_id": "speed_impact",
        "question_id": "q3",
        "slot_name": "속도가 툴 선택에 미치는 영향",
    },
    {
        "slot_id": "cost_impact",
        "question_id": "q3",
        "slot_name": "비용이 툴 선택에 미치는 영향",
    },
    {
        "slot_id": "autonomy_impact",
        "question_id": "q3",
        "slot_name": "자율성이 툴 선택에 미치는 영향",
    },
    {
        "slot_id": "feature_request",
        "question_id": "q4",
        "slot_name": "사용자가 직접 요구한 핵심 기능",
    },
    {
        "slot_id": "switching_trigger",
        "question_id": "q4",
        "slot_name": "OpenAI 도구 전환을 촉진할 수 있는 조건",
    },
]


# =========================================================
# Analyzer 인터페이스
# =========================================================

class ReportAnalyzer(Protocol):

    async def analyze(
        self,
        session: Session,
        transcript: list[Turn],
        instructions: list[Instruction],
    ) -> dict[str, Any]:
        ...


# =========================================================
# Azure OpenAI 미연결 시 Stub
# =========================================================

class StubReportAnalyzer:

    async def analyze(
        self,
        session: Session,
        transcript: list[Turn],
        instructions: list[Instruction],
    ) -> dict[str, Any]:

        return {
            "participant_context": {
                "primary_tool": "[STUB]",
                "secondary_tools": [],
                "usage_pattern": [],
            },

            "executive_summary": {
                "core_insight": "[STUB]",
                "current_preference": "[STUB]",
                "primary_driver": "[STUB]",
                "primary_pain_point": "[STUB]",
                "top_switching_trigger": "[STUB]",
            },

            "research_coverage": {
                "overall_coverage": "low",
                "items": [],
            },

            "slot_coverage": {
                "overall_coverage": "low",
                "items": [
                    {
                        "slot_id": slot["slot_id"],
                        "question_id": slot["question_id"],
                        "slot_name": slot["slot_name"],
                        "coverage": "not_covered",
                        "reason": "Azure OpenAI 미연결",
                        "evidence_ids": [],
                        "missing_information": [],
                    }
                    for slot in SLOT_DEFINITIONS
                ],
            },

            "key_findings": [],

            "preference_drivers": [],

            "pain_points": [],

            "switching_analysis": {
                "retention_drivers": [],
                "switching_barriers": [],
                "switching_triggers": [],
                "switching_signal": "unclear",
            },

            "feature_opportunities": [],

            "observer_intervention_analysis": [],

            "researcher_attention": [],

            "analysis_metadata": {
                "mode": "azure_openai",
            },
        }


# =========================================================
# GPT-5.1 실제 Analyzer
# =========================================================

class AzureOpenAIReportAnalyzer:

    def __init__(self) -> None:
        from openai import AsyncOpenAI

        settings = get_settings()

        self._deployment = (
            settings.azure_openai_chat_deployment
        )

        self._client = AsyncOpenAI(
            api_key=settings.azure_openai_api_key,
            base_url=(
                settings.azure_openai_endpoint.rstrip("/")
                + "/openai/v1/"
            ),
            timeout=120.0,
        )


    async def analyze(
        self,
        session: Session,
        transcript: list[Turn],
        instructions: list[Instruction],
    ) -> dict[str, Any]:

        # =================================================
        # 1. Evidence Library
        # =================================================

        interviewee_turns = [
            turn
            for turn in transcript
            if turn.speaker == "interviewee"
        ]

        evidence_library: list[dict[str, Any]] = []

        for number, turn in enumerate(
            interviewee_turns,
            start=1,
        ):
            evidence_library.append(
                {
                    "evidence_id": f"E{number:03d}",
                    "turn_index": turn.index,
                    "speaker": turn.speaker,
                    "quote": turn.text,
                    "created_at": turn.created_at.isoformat(),
                }
            )

        allowed_evidence_ids = {
            item["evidence_id"]
            for item in evidence_library
        }


        # =================================================
        # 2. GPT에 전달할 데이터
        # =================================================

        input_data = {
            "research_title": session.title,

            "session": {
                "session_id": session.id,
                "duration_minutes": session.duration_minutes,
                "started_at": (
                    session.started_at.isoformat()
                    if session.started_at
                    else None
                ),
                "ended_at": (
                    session.ended_at.isoformat()
                    if session.ended_at
                    else None
                ),
            },

            "questions": [
                question.model_dump(mode="json")
                for question in session.questions
            ],

            "transcript": [
                turn.model_dump(mode="json")
                for turn in transcript
            ],

            "observer_instructions": [
                instruction.model_dump(mode="json")
                for instruction in instructions
            ],

            "evidence_library": evidence_library,

            "required_slots": SLOT_DEFINITIONS,
        }


        # =================================================
        # 3. 분석 Prompt
        # =================================================

        system_prompt = """
당신은 기업 시장조사 및 UX Research 전문 정성 인터뷰 분석가입니다.

제공된 인터뷰 1건을 분석하여
Individual Interview Report를 작성하세요.


==================================================
[Evidence 규칙]
==================================================

Evidence는 반드시 speaker가 interviewee인
실제 응답자의 발언만 사용할 수 있습니다.

assistant가 한 질문,
진행자가 질문 속에 넣은 주장,
가정,
유도 문구는 응답자의 Evidence가 아닙니다.

모든 주요 분석은 제공된 Evidence Library의
evidence_id와 연결하세요.

존재하지 않는 evidence_id를 만들지 마세요.


==================================================
[일반화 금지]
==================================================

현재 데이터는 한 명의 인터뷰입니다.

"개발자들은"
"사용자들은"
"시장에서는"
"대부분의 사람들은"

같은 표현으로 일반화하지 마세요.

대신

"이 응답자는"
"본 인터뷰에서는"
"이 참여자의 경험에서는"

처럼 표현하세요.


==================================================
[Question Coverage]
==================================================

research_coverage는 질문 단위 Coverage입니다.

질문을 단순히 했는지 여부가 아니라,
연구자가 해당 질문에서 얻고 싶었던 정보가
실제 응답으로 얼마나 확보됐는지를 평가하세요.

coverage:

high
medium
low
not_covered


==================================================
[Slot Coverage]
==================================================

required_slots에 제공된 모든 Slot을
정확히 하나씩 평가해야 합니다.

새로운 Slot을 임의로 생성하지 마세요.

기존 Slot을 삭제하거나 생략하지 마세요.

각 Slot에는 반드시 다음 필드를 작성하세요.

slot_id
question_id
slot_name
coverage
reason
evidence_ids
missing_information


coverage 판단 기준:

high:
해당 정보가 명확하고 구체적으로 확보됐으며
판단에 활용할 수 있는 충분한 Evidence가 있음.

medium:
핵심 내용은 확보됐지만
세부 설명이나 사례가 일부 부족함.

low:
관련 언급은 있으나
연구 판단에 사용하기에는 정보가 부족함.

not_covered:
해당 정보를 인터뷰에서 확인하지 못함.


중요:

응답이 짧게 언급되었다는 이유만으로
무조건 high를 주지 마세요.

예를 들어

"속도는 괜찮다"
"비용은 감수할 수 있다"

정도의 발언만 있는 경우,

그 요인이 제품 선택에 미치는 세부 영향까지
충분히 확인한 것은 아닐 수 있습니다.

이 경우 medium 또는 low가 더 적절할 수 있습니다.


==================================================
[Key Findings]
==================================================

단순한 답변 요약이 아니라
연구 목적과 직접적으로 관련된 중요한 발견을 추출하세요.

각 Finding에는 실제 evidence_ids를 연결하세요.


==================================================
[Preference Drivers]
==================================================

응답자가 현재 도구를 선택하고
계속 사용하게 만드는 실질적인 이유를 분석하세요.

단순 기능 언급과 실제 선택 이유를 구분하세요.


==================================================
[Pain Points]
==================================================

각 Pain Point는 다음을 구분하세요.

- 어떤 문제가 발생했는가
- 어떤 상황에서 발생했는가
- 사용자에게 어떤 영향을 주는가
- 심각도는 어느 정도인가


==================================================
[Switching Analysis]
==================================================

retention_drivers:
현재 사용하는 도구를 계속 사용하게 만드는 이유

switching_barriers:
다른 도구로 이동하기 어렵게 만드는 요인

switching_triggers:
다른 도구를 새롭게 고려하게 만드는 조건

switching_signal:

strong
moderate
weak
unclear


응답자가

"이 기능이 생기면 불편이 줄어들 것 같다"

라고 말했다고 해서

"이 기능이 생기면 반드시 제품을 바꾸겠다"

라고 해석하지 마세요.

직접적인 전환 의사가 확인되지 않았다면
switching_signal을 과도하게 높이지 마세요.


==================================================
[Feature Opportunities]
==================================================

source_type은 반드시 다음 둘 중 하나입니다.


explicit_user_request

응답자가 직접 원하는 기능이나 개선점을 말함.


derived_opportunity

응답자는 문제만 언급했고,
그 문제를 해결하기 위한 기능은 분석자가 도출함.


AI가 도출한 제품 아이디어를
응답자가 직접 요구한 것처럼 표현하지 마세요.


==================================================
[Observer Intervention Analysis]
==================================================

observer_instructions가 존재하는 경우 분석하세요.

참관자의 지시 이후
실제로 새로운 구체적 Evidence가 확보되었는지 확인하세요.

resulting_evidence_ids에는
실제로 해당 지시 이후 확보된 Evidence만 연결하세요.

확실한 인과관계를 확인하기 어렵다면
억지로 Evidence를 연결하지 마세요.

research_value:

high
medium
low


==================================================
[Researcher Attention]
==================================================

현재 인터뷰만으로 충분히 확인되지 않은 정보,
모호한 정보,
추가 인터뷰에서 확인해야 할 내용을 작성하세요.

확인되지 않은 내용을 추측으로 채우지 마세요.


==================================================
[출력]
==================================================

제공된 JSON Schema를 정확히 따라야 합니다.

Schema에 없는 필드를 추가하지 마세요.

필수 필드를 누락하지 마세요.
"""


        # =================================================
        # 4. Pydantic → JSON Schema
        # =================================================

        output_schema = (
            IndividualInterviewAnalysis
            .model_json_schema()
        )


        # =================================================
        # 5. GPT-5.1 Structured Output
        # =================================================

        try:
            response = await self._client.responses.create(
                model=self._deployment,

                instructions=system_prompt,

                input=(
                    "아래 인터뷰 데이터를 분석하세요.\n"
                    "required_slots에 정의된 모든 Slot을 "
                    "반드시 하나씩 평가하세요.\n"
                    "결과는 JSON Schema를 정확히 따르세요.\n\n"
                    + json.dumps(
                        input_data,
                        ensure_ascii=False,
                        indent=2,
                    )
                ),

                reasoning={
                    "effort": "none"
                },

                max_output_tokens=12000,

                text={
                    "verbosity": "low",

                    "format": {
                        "type": "json_schema",
                        "name": "individual_interview_analysis",
                        "schema": output_schema,
                        "strict": True,
                    },
                },
            )

        except Exception:
            logger.exception(
                "Azure OpenAI 리포트 분석 호출 실패"
            )
            raise


        # =================================================
        # 6. 응답 확인
        # =================================================

        content = response.output_text

        if not content:
            raise ValueError(
                "Azure OpenAI가 빈 분석 결과를 반환했습니다."
            )


        # =================================================
        # 7. JSON Parsing
        # =================================================

        try:
            raw_result = json.loads(content)

        except json.JSONDecodeError:
            logger.exception(
                "Azure OpenAI 결과 JSON 파싱 실패. "
                "응답 앞부분=%s",
                content[:500],
            )
            raise


        # =================================================
        # 8. Evidence ID 검증
        # =================================================

        self._sanitize_evidence_ids(
            raw_result,
            allowed_evidence_ids,
        )


        # =================================================
        # 9. Slot 검증
        # =================================================

        self._validate_slots(
            raw_result
        )


        # =================================================
        # 10. Pydantic 최종 검증
        # =================================================

        validated = (
            IndividualInterviewAnalysis
            .model_validate(raw_result)
        )

        return validated.model_dump(
            mode="json"
        )


    # =====================================================
    # Evidence ID 검증
    # =====================================================

    def _sanitize_evidence_ids(
        self,
        value: Any,
        allowed_evidence_ids: set[str],
    ) -> None:

        if isinstance(value, dict):

            for key, item in value.items():

                if (
                    key in {
                        "evidence_ids",
                        "resulting_evidence_ids",
                    }
                    and isinstance(item, list)
                ):
                    value[key] = [
                        evidence_id
                        for evidence_id in item
                        if evidence_id
                        in allowed_evidence_ids
                    ]

                else:
                    self._sanitize_evidence_ids(
                        item,
                        allowed_evidence_ids,
                    )

        elif isinstance(value, list):

            for item in value:
                self._sanitize_evidence_ids(
                    item,
                    allowed_evidence_ids,
                )


    # =====================================================
    # Slot 검증
    # =====================================================

    def _validate_slots(
        self,
        result: dict[str, Any],
    ) -> None:

        required_ids = [
            slot["slot_id"]
            for slot in SLOT_DEFINITIONS
        ]

        items = (
            result
            .get("slot_coverage", {})
            .get("items", [])
        )

        result_ids = [
            item.get("slot_id")
            for item in items
        ]

        missing = (
            set(required_ids)
            - set(result_ids)
        )

        unexpected = (
            set(result_ids)
            - set(required_ids)
        )

        duplicates = {
            slot_id
            for slot_id in result_ids
            if result_ids.count(slot_id) > 1
        }

        if missing:
            raise ValueError(
                f"누락된 Slot: {sorted(missing)}"
            )

        if unexpected:
            raise ValueError(
                f"정의되지 않은 Slot: {sorted(unexpected)}"
            )

        if duplicates:
            raise ValueError(
                f"중복된 Slot: {sorted(duplicates)}"
            )

        if len(result_ids) != len(required_ids):
            raise ValueError(
                "Slot 개수가 정의된 Slot 개수와 일치하지 않습니다."
            )


# =========================================================
# Analyzer 선택
# =========================================================

_analyzer: ReportAnalyzer | None = None


def get_report_analyzer() -> ReportAnalyzer:

    global _analyzer

    if _analyzer is None:

        settings = get_settings()

        if settings.use_azure_openai:

            logger.info(
                "AzureOpenAIReportAnalyzer 사용"
            )

            _analyzer = (
                AzureOpenAIReportAnalyzer()
            )

        else:

            logger.warning(
                "Azure OpenAI 설정 없음 - "
                "StubReportAnalyzer 사용"
            )

            _analyzer = (
                StubReportAnalyzer()
            )

    return _analyzer