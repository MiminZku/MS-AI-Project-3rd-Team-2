from __future__ import annotations

import json
import logging
from typing import Any, Protocol

from app.core.config import get_settings
from app.schemas.report_analysis import (
    IndividualInterviewAnalysis,
)
from app.schemas.session import (
    Instruction,
    Session,
    Turn,
)
from app.schemas.study import ResearchStudy


logger = logging.getLogger(__name__)


# =========================================================
# Analyzer Interface
# =========================================================

class ReportAnalyzer(Protocol):

    async def analyze(
        self,
        session: Session,
        transcript: list[Turn],
        instructions: list[Instruction],
        study: ResearchStudy | None,
    ) -> dict[str, Any]:
        ...


# =========================================================
# Stub Analyzer
# =========================================================

class StubReportAnalyzer:

    async def analyze(
        self,
        session: Session,
        transcript: list[Turn],
        instructions: list[Instruction],
        study: ResearchStudy | None,
    ) -> dict[str, Any]:

        slots = (
            study.information_slots
            if study
            else []
        )

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
                        "slot_id": slot.slot_id,
                        "question_id": slot.question_id,
                        "slot_name": slot.slot_name,
                        "coverage": "not_covered",
                        "reason": (
                            "Azure OpenAI 미연결"
                        ),
                        "evidence_ids": [],
                        "missing_information": [
                            slot.description
                        ],
                    }
                    for slot in slots
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
# Azure OpenAI Analyzer
# =========================================================

class AzureOpenAIReportAnalyzer:

    def __init__(self) -> None:

        from openai import AsyncOpenAI

        settings = get_settings()

        self._deployment = (
            settings.azure_openai_chat_deployment
        )

        self._client = AsyncOpenAI(
            api_key=(
                settings.azure_openai_api_key
            ),
            base_url=(
                settings
                .azure_openai_endpoint
                .rstrip("/")
                + "/openai/v1/"
            ),
            timeout=120.0,
        )


    async def analyze(
        self,
        session: Session,
        transcript: list[Turn],
        instructions: list[Instruction],
        study: ResearchStudy | None,
    ) -> dict[str, Any]:

        # =================================================
        # 1. Evidence Library
        # =================================================

        interviewee_turns = [
            turn
            for turn in transcript
            if turn.speaker == "interviewee"
        ]

        evidence_library: list[
            dict[str, Any]
        ] = []

        for number, turn in enumerate(
            interviewee_turns,
            start=1,
        ):
            evidence_library.append(
                {
                    "evidence_id": (
                        f"E{number:03d}"
                    ),
                    "turn_index": turn.index,
                    "speaker": turn.speaker,
                    "quote": turn.text,
                    "created_at": (
                        turn.created_at
                        .isoformat()
                    ),
                }
            )

        allowed_evidence_ids = {
            item["evidence_id"]
            for item in evidence_library
        }

        # =================================================
        # 2. Study에서 자동 생성된 Slot 가져오기
        # =================================================

        required_slots = []

        if study:
            required_slots = [
                slot.model_dump(
                    mode="json"
                )
                for slot
                in study.information_slots
            ]

        # =================================================
        # 3. GPT 입력 데이터
        # =================================================

        input_data = {
            "research": {
                "study_id": (
                    study.id
                    if study
                    else None
                ),
                "title": (
                    study.title
                    if study
                    else session.title
                ),
                "research_purpose": (
                    study.research_purpose
                    if study
                    else None
                ),
            },

            "session": {
                "session_id": session.id,
                "study_id": session.study_id,
                "duration_minutes": (
                    session.duration_minutes
                ),
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
                question.model_dump(
                    mode="json"
                )
                for question
                in session.questions
            ],

            "required_slots": (
                required_slots
            ),

            "transcript": [
                turn.model_dump(
                    mode="json"
                )
                for turn
                in transcript
            ],

            "observer_instructions": [
                instruction.model_dump(
                    mode="json"
                )
                for instruction
                in instructions
            ],

            "evidence_library": (
                evidence_library
            ),
        }

        # =================================================
        # 4. Analysis Prompt
        # =================================================

        system_prompt = """
당신은 기업 시장조사 및 UX Research 전문
정성 인터뷰 분석가입니다.

제공된 조사 목적, 질문지, Information Slot,
인터뷰 Transcript를 바탕으로
한 명의 Individual Interview Report를 작성하세요.


==================================================
[가장 중요한 원칙]
==================================================

이번 조사의 질문과 Information Slot은
조사마다 달라질 수 있습니다.

특정 산업, 제품, 브랜드, 기술 주제를
미리 가정하지 마세요.

반드시 입력으로 제공된

- research
- questions
- required_slots
- transcript

를 기준으로 현재 조사만 분석하세요.


==================================================
[Evidence 규칙]
==================================================

Evidence는 반드시
speaker가 interviewee인
실제 응답자의 발언만 사용할 수 있습니다.

assistant의 질문,
진행자가 질문에 넣은 주장,
가정,
유도 문구는
응답자의 Evidence가 아닙니다.

모든 주요 분석에는
Evidence Library에 실제 존재하는
evidence_id를 연결하세요.

존재하지 않는 evidence_id를
새로 만들지 마세요.


==================================================
[일반화 금지]
==================================================

현재 데이터는
한 명의 인터뷰 결과입니다.

한 사람의 발언을 근거로

"사용자들은"
"고객들은"
"시장에서는"
"대부분의 사람들은"

처럼 일반화하지 마세요.

대신

"이 응답자는"
"본 인터뷰에서는"
"이 참여자의 경험에서는"

처럼 표현하세요.


==================================================
[Research Coverage]
==================================================

research_coverage는
질문 단위 Coverage입니다.

질문을 했는지를 평가하는 것이 아닙니다.

해당 질문을 통해
연구자가 알고 싶었던 정보가
실제 응답에서 얼마나 확보됐는지를
평가하세요.

coverage 값:

high
medium
low
not_covered


==================================================
[Slot Coverage]
==================================================

required_slots는
이 ResearchStudy 생성 시
조사 목적과 질문지를 분석해
미리 확정한 Information Slot입니다.

required_slots가 존재한다면
모든 Slot을 정확히 하나씩 평가하세요.

Slot을 새로 만들지 마세요.

Slot을 삭제하거나 누락하지 마세요.

각 Slot에는 반드시:

- slot_id
- question_id
- slot_name
- coverage
- reason
- evidence_ids
- missing_information

을 작성하세요.


coverage 기준:

high:
명확한 답변과 구체적인 근거가
충분히 확보됨.

medium:
핵심 정보는 있지만
구체적인 설명이나 사례가 일부 부족함.

low:
관련 언급은 있으나
연구 판단에 사용하기에는 부족함.

not_covered:
해당 정보를 실제 인터뷰에서
확인하지 못함.


Slot의 importance가 high라고 해서
자동으로 coverage도 high가 되는 것은 아닙니다.

importance는
'그 정보가 연구에서 얼마나 중요한지'이고,

coverage는
'이번 인터뷰에서 실제로 얼마나 확보됐는지'입니다.


required_slots가 빈 배열이라면

slot_coverage.items는
빈 배열로 반환하세요.


==================================================
[Key Findings]
==================================================

단순 발언 요약이 아니라
현재 research_purpose와 관련해
의미 있는 발견을 추출하세요.

각 Finding은 실제 Evidence와
연결되어야 합니다.


==================================================
[Preference Drivers]
==================================================

현재 조사에서
실제 선택, 선호, 유지 요인이 확인된 경우
Evidence를 기반으로 분석하세요.

그러한 내용이 조사에서 확인되지 않았다면
억지로 생성하지 마세요.


==================================================
[Pain Points]
==================================================

Pain Point가 실제로 확인된 경우:

- 어떤 문제인지
- 어떤 상황에서 발생하는지
- 응답자에게 어떤 영향을 주는지
- 심각도

를 구분하세요.

확인되지 않은 문제를
추측해서 만들지 마세요.


==================================================
[Switching Analysis]
==================================================

현재 조사에서
전환, 이탈, 유지와 관련된 Evidence가
존재할 경우에만 적극적으로 분석하세요.

retention_drivers:
현재 선택을 유지하게 만드는 요인

switching_barriers:
다른 선택으로 이동하는 것을 방해하는 요인

switching_triggers:
다른 선택을 고려하게 만드는 조건

switching_signal:

strong
moderate
weak
unclear


전환과 무관한 조사이거나
전환 Evidence가 없다면

빈 배열과
switching_signal = unclear

을 사용하세요.

"불편이 줄어들 것 같다"는 말과
"실제로 전환하겠다"는 말은 다릅니다.


==================================================
[Feature Opportunities]
==================================================

제품/서비스 개선 기회가
실제 인터뷰에서 확인될 경우 분석하세요.

source_type:

explicit_user_request
응답자가 직접 기능이나 개선을 요구함.

derived_opportunity
응답자는 문제만 말했고
분석자가 해결 기회를 도출함.

응답자가 직접 말하지 않은 아이디어를
사용자 직접 요구처럼 표현하지 마세요.

기능 제안과 무관한 조사라면
빈 배열을 사용할 수 있습니다.


==================================================
[Observer Intervention]
==================================================

observer_instructions가 있는 경우,

해당 지시 이후 실제로
새로운 Evidence가 확보됐는지 분석하세요.

resulting_evidence_ids에는
실제 확보된 Evidence만 연결하세요.

억지로 인과관계를 만들지 마세요.


==================================================
[Researcher Attention]
==================================================

현재 인터뷰에서

- 부족했던 정보
- 애매했던 내용
- 추가 확인이 필요한 내용
- Coverage가 낮은 핵심 Slot

등을 연구자에게 알려주세요.

확인되지 않은 내용을
추측으로 채우지 마세요.


==================================================
[출력]
==================================================

제공된 JSON Schema를
정확하게 따라야 합니다.

Schema에 없는 필드를 추가하지 마세요.

필수 필드를 누락하지 마세요.
"""

        # =================================================
        # 5. Structured Output Schema
        # =================================================

        output_schema = (
            IndividualInterviewAnalysis
            .model_json_schema()
        )

        # =================================================
        # 6. GPT-5.1 호출
        # =================================================

        try:

            response = (
                await self._client.responses.create(
                    model=self._deployment,

                    instructions=system_prompt,

                    input=(
                        "아래 조사 및 인터뷰 데이터를 "
                        "분석하세요.\n"
                        "required_slots가 존재하면 "
                        "모든 Slot을 정확히 하나씩 "
                        "평가하세요.\n\n"
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
                            "name": (
                                "individual_"
                                "interview_analysis"
                            ),
                            "schema": (
                                output_schema
                            ),
                            "strict": True,
                        },
                    },
                )
            )

        except Exception:

            logger.exception(
                "Azure OpenAI 리포트 분석 호출 실패"
            )

            raise

        # =================================================
        # 7. Response 확인
        # =================================================

        content = response.output_text

        if not content:
            raise ValueError(
                "Azure OpenAI가 빈 분석 결과를 "
                "반환했습니다."
            )

        # =================================================
        # 8. JSON Parsing
        # =================================================

        try:

            raw_result = json.loads(
                content
            )

        except json.JSONDecodeError:

            logger.exception(
                "Azure OpenAI 결과 JSON 파싱 실패. "
                "응답 앞부분=%s",
                content[:500],
            )

            raise

        # =================================================
        # 9. Evidence ID 검증
        # =================================================

        self._sanitize_evidence_ids(
            raw_result,
            allowed_evidence_ids,
        )

        # =================================================
        # 10. Dynamic Slot 검증
        # =================================================

        self._validate_slots(
            result=raw_result,
            required_slots=required_slots,
        )

        # =================================================
        # 11. Pydantic 최종 검증
        # =================================================

        validated = (
            IndividualInterviewAnalysis
            .model_validate(
                raw_result
            )
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
                    and isinstance(
                        item,
                        list,
                    )
                ):

                    value[key] = [
                        evidence_id
                        for evidence_id
                        in item
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
    # Dynamic Slot 검증
    # =====================================================

    def _validate_slots(
        self,
        result: dict[str, Any],
        required_slots: list[
            dict[str, Any]
        ],
    ) -> None:

        required_ids = [
            slot["slot_id"]
            for slot in required_slots
        ]

        items = (
            result
            .get(
                "slot_coverage",
                {},
            )
            .get(
                "items",
                [],
            )
        )

        result_ids = [
            item.get("slot_id")
            for item in items
        ]

        # ---------------------------------------------
        # Study Slot이 없는 legacy Session
        # ---------------------------------------------

        if not required_ids:

            if result_ids:
                raise ValueError(
                    "Study Slot이 없는데 "
                    "새로운 Slot이 생성되었습니다."
                )

            return

        # ---------------------------------------------
        # 누락
        # ---------------------------------------------

        missing = (
            set(required_ids)
            - set(result_ids)
        )

        # ---------------------------------------------
        # 정의되지 않은 Slot
        # ---------------------------------------------

        unexpected = (
            set(result_ids)
            - set(required_ids)
        )

        # ---------------------------------------------
        # 중복 Slot
        # ---------------------------------------------

        duplicates = {
            slot_id
            for slot_id in result_ids
            if result_ids.count(
                slot_id
            ) > 1
        }

        if missing:
            raise ValueError(
                "누락된 Slot: "
                f"{sorted(missing)}"
            )

        if unexpected:
            raise ValueError(
                "정의되지 않은 Slot: "
                f"{sorted(unexpected)}"
            )

        if duplicates:
            raise ValueError(
                "중복된 Slot: "
                f"{sorted(duplicates)}"
            )

        if (
            len(result_ids)
            != len(required_ids)
        ):
            raise ValueError(
                "Slot 개수가 ResearchStudy에 "
                "저장된 Slot 개수와 일치하지 않습니다."
            )


# =========================================================
# Analyzer Singleton
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