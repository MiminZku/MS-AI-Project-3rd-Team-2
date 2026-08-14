from __future__ import annotations

import json
import logging
from typing import Any, Protocol

from app.core.config import get_settings
from app.schemas.session import Instruction, Session, Turn

logger = logging.getLogger(__name__)


# =========================================================
# Report Analyzer 인터페이스
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
# Azure OpenAI가 없을 때 사용하는 STUB
# =========================================================

class StubReportAnalyzer:
    """
    Azure OpenAI가 연결되지 않았을 때 사용하는 테스트 분석기.
    실제 AI 분석은 하지 않고 리포트 파이프라인만 검증한다.
    """

    async def analyze(
        self,
        session: Session,
        transcript: list[Turn],
        instructions: list[Instruction],
    ) -> dict[str, Any]:

        interviewee_turns = [
            turn
            for turn in transcript
            if turn.speaker == "interviewee"
        ]

        return {
            "participant_context": {
                "primary_tool": "[STUB] 분석 전",
                "secondary_tools": [],
                "usage_pattern": [],
            },

            "executive_summary": {
                "core_insight": (
                    "[STUB] Azure OpenAI가 연결되면 "
                    "인터뷰 핵심 인사이트가 생성됩니다."
                ),
                "current_preference": "[STUB]",
                "primary_driver": "[STUB]",
                "primary_pain_point": "[STUB]",
                "top_switching_trigger": "[STUB]",
            },

            "research_coverage": {
                "overall_coverage": None,
                "items": [
                    {
                        "question_id": question.id,
                        "question": question.text,
                        "coverage": "not_analyzed",
                        "reason": "",
                        "evidence_ids": [],
                        "missing_information": [],
                    }
                    for question in session.questions
                ],
            },

            "key_findings": [],

            "preference_drivers": [],

            "pain_points": [],

            "switching_analysis": {
                "retention_drivers": [],
                "switching_barriers": [],
                "switching_triggers": [],
                "switching_signal": "not_analyzed",
            },

            "feature_opportunities": [],

            "researcher_attention": [
                {
                    "topic": "Azure OpenAI",
                    "reason": (
                        "현재 Azure OpenAI가 연결되지 않아 "
                        "실제 정성 분석은 수행되지 않았습니다."
                    ),
                    "priority": "high",
                }
            ],

            "analysis_metadata": {
                "mode": "stub",
                "interviewee_turn_count": len(interviewee_turns),
                "instruction_count": len(instructions),
            },
        }


# =========================================================
# Azure OpenAI GPT-5.1 실제 분석기
# =========================================================

class AzureOpenAIReportAnalyzer:
    """
    인터뷰 종료 후 전체 transcript를 분석하여
    Individual Interview Report 데이터를 생성한다.
    """

    def __init__(self) -> None:
        from openai import AsyncOpenAI

        settings = get_settings()

        # Azure에서 만든 Deployment Name
        # 현재 우리 프로젝트에서는 gpt-5.1
        self._deployment = settings.azure_openai_chat_deployment

        # Azure Foundry v1 endpoint 사용
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
        # 1. 응답자 발언만 Evidence Library로 생성
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

        # AI가 사용할 수 있는 정상 Evidence ID 목록
        allowed_evidence_ids = {
            item["evidence_id"]
            for item in evidence_library
        }

        # =================================================
        # 2. Azure OpenAI에 전달할 데이터
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
        }

        # =================================================
        # 3. 정성 인터뷰 분석 프롬프트
        # =================================================

        system_prompt = """
당신은 기업 시장조사와 UX Research를 수행하는
전문 정성 인터뷰 분석가입니다.

제공된 인터뷰를 분석하여
Individual Interview Report를 생성하세요.

반드시 JSON 객체 하나만 출력하세요.


==================================================
[가장 중요한 Evidence 규칙]
==================================================

1. interviewee의 실제 발언만
   사용자 Evidence로 취급합니다.

2. assistant가 한 질문은
   사용자의 의견이 아닙니다.

3. 질문지 자체에 포함된 주장이나 가정도
   사용자의 의견이 아닙니다.

예를 들어 진행자가

"모델 성능은 OpenAI가 최고인데
터미널에서는 Claude Code를 사용한다는 이야기가 있습니다."

라고 질문했다고 해서

"이 응답자는 OpenAI 모델 성능이 최고라고 생각한다."

라고 분석하면 안 됩니다.

응답자가 실제로 동의하거나
자신의 경험을 설명한 내용만 Evidence로 사용합니다.


==================================================
[Evidence ID 규칙]
==================================================

모든 중요한 분석에는
제공된 Evidence Library의 evidence_id를 연결하세요.

특히 다음 항목에는 evidence_ids가 필요합니다.

- usage_pattern
- key_findings
- preference_drivers
- pain_points
- retention_drivers
- switching_barriers
- switching_triggers
- feature_opportunities
- research_coverage

존재하지 않는 Evidence ID를 만들지 마세요.

응답자의 실제 발언과 연결할 수 없는 내용은
강한 Finding으로 만들지 마세요.


==================================================
[일반화 금지]
==================================================

이 데이터는 한 명의 인터뷰입니다.

따라서

"개발자들은"
"사용자들은"
"시장에서는"

같은 식으로 일반화하지 마세요.

대신

"이 응답자는"
"본 인터뷰에서는"
"이 참여자의 경험에서는"

처럼 표현하세요.


==================================================
[숫자 생성 금지]
==================================================

인터뷰에 존재하지 않는

- 확률
- 시장 비율
- 고객 비율
- 전환율
- 임의의 점수

를 생성하지 마세요.

Switching likelihood 역시 임의의 %로 만들지 말고

strong
moderate
weak
unclear

중 하나로 표현하세요.


==================================================
[Research Coverage]
==================================================

Coverage는 단순히 질문을 했는지를 판단하는 것이 아닙니다.

연구자가 해당 질문을 통해
알고 싶었던 정보가 실제 답변으로 확보됐는지를 판단하세요.

coverage는 다음 중 하나입니다.

high
medium
low
not_covered

답변이 추상적이거나 구체 사례가 부족하다면
missing_information에 부족한 정보를 작성하세요.


==================================================
[Key Findings]
==================================================

인터뷰 전체를 단순 요약하지 마세요.

연구 목적에 중요한 의미가 있는 발견만 추출하세요.

예:

- Workflow Continuity
- Context Management
- Agent Autonomy
- Manual Intervention
- Terminal UX
- Switching Barrier
- Switching Trigger

단, 위 예시에 억지로 맞추지 말고
실제 응답 내용에 근거하세요.


==================================================
[Pain Point]
==================================================

Pain Point에는 다음을 구분해서 작성하세요.

- 어떤 문제가 발생했는가
- 어떤 상황에서 발생했는가
- 사용자에게 어떤 영향을 줬는가
- 심각도는 어느 정도인가


==================================================
[Preference Driver]
==================================================

현재 제품/도구를 선택하거나 계속 사용하는
실질적인 이유를 추출하세요.

단순 기능 언급과
실제 선택 요인을 구분하세요.


==================================================
[Switching Analysis]
==================================================

retention_drivers:
현재 사용 중인 제품을 계속 쓰게 하는 이유

switching_barriers:
다른 제품으로 이동하지 못하게 하거나
이동을 꺼리게 하는 장애물

switching_triggers:
다른 제품으로 전환하게 만들 수 있는 조건이나 기능

switching_signal:
strong / moderate / weak / unclear


==================================================
[Feature Opportunity]
==================================================

인터뷰 발언을 제품 기회로 연결하세요.

각 Feature Opportunity에는

- feature
- problem
- user_need
- expected_value
- priority
- evidence_ids

를 포함하세요.

응답자가 직접 원하는 기능을 말한 경우
가장 강한 기회로 취급할 수 있습니다.


==================================================
[Researcher Attention]
==================================================

AI가 억지로 결론을 만들면 안 되는 부분을 기록하세요.

예:

- 구체 사례 부족
- Cost 영향 확인 부족
- Speed 영향 확인 부족
- 추가 인터뷰 필요
- 표현이 모호함

이 영역에는 반드시
추가 확인이 필요한 이유를 작성하세요.


==================================================
[출력 JSON 구조]
==================================================

반드시 아래 구조를 유지하세요.

{
  "participant_context": {
    "primary_tool": "",
    "secondary_tools": [],
    "usage_pattern": [
      {
        "situation": "",
        "preferred_tool": "",
        "evidence_ids": []
      }
    ]
  },

  "executive_summary": {
    "core_insight": "",
    "current_preference": "",
    "primary_driver": "",
    "primary_pain_point": "",
    "top_switching_trigger": ""
  },

  "research_coverage": {
    "overall_coverage": "high",
    "items": [
      {
        "question_id": "",
        "question": "",
        "coverage": "high",
        "reason": "",
        "evidence_ids": [],
        "missing_information": []
      }
    ]
  },

  "key_findings": [
    {
      "title": "",
      "summary": "",
      "evidence_strength": "strong",
      "evidence_ids": []
    }
  ],

  "preference_drivers": [
    {
      "driver": "",
      "strength": "high",
      "description": "",
      "evidence_ids": []
    }
  ],

  "pain_points": [
    {
      "pain_point": "",
      "severity": "high",
      "situation": "",
      "user_impact": "",
      "evidence_ids": []
    }
  ],

  "switching_analysis": {
    "retention_drivers": [
      {
        "driver": "",
        "evidence_ids": []
      }
    ],

    "switching_barriers": [
      {
        "barrier": "",
        "evidence_ids": []
      }
    ],

    "switching_triggers": [
      {
        "trigger": "",
        "evidence_ids": []
      }
    ],

    "switching_signal": "strong"
  },

  "feature_opportunities": [
    {
      "feature": "",
      "problem": "",
      "user_need": "",
      "expected_value": "",
      "priority": "high",
      "evidence_ids": []
    }
  ],

  "researcher_attention": [
    {
      "topic": "",
      "reason": "",
      "priority": "high"
    }
  ],

  "analysis_metadata": {
    "mode": "azure_openai"
  }
}
"""

        # =================================================
        # 4. GPT-5.1 Responses API 호출
        # =================================================

        try:
            response = await self._client.responses.create(
                model=self._deployment,

                instructions=system_prompt,

                input=(
    "아래 인터뷰 데이터를 분석하고 결과를 반드시 JSON 객체로만 반환하세요.\n\n"
    + json.dumps(
        input_data,
        ensure_ascii=False,
        indent=2,
    )
),
                max_output_tokens=10000,

                text={
                    "format": {
                        "type": "json_object"
                    }
                },
            )

        except Exception:
            logger.exception(
                "Azure OpenAI 리포트 분석 호출 실패"
            )
            raise

        # Responses API 결과 텍스트
        content = response.output_text or "{}"

        # =================================================
        # 5. JSON 문자열 → Python dict
        # =================================================

        try:
            result = json.loads(content)

        except json.JSONDecodeError:
            logger.exception(
                "Azure OpenAI 리포트 결과 JSON 파싱 실패. "
                "응답 앞부분=%s",
                content[:500],
            )
            raise

        # =================================================
        # 6. AI가 존재하지 않는 Evidence ID를
        #    만들어냈을 경우 제거
        # =================================================

        self._sanitize_evidence_ids(
            result,
            allowed_evidence_ids,
        )

        # 분석 방식은 서버가 확정
        result["analysis_metadata"] = {
            "mode": "azure_openai",
            "deployment": self._deployment,
        }

        return result

    # =====================================================
    # Evidence ID 검증
    # =====================================================

    def _sanitize_evidence_ids(
        self,
        value: Any,
        allowed_evidence_ids: set[str],
    ) -> None:
        """
        AI 결과 전체를 돌면서 evidence_ids를 검사한다.

        Evidence Library에 없는 ID는 제거한다.
        """

        if isinstance(value, dict):

            for key, item in value.items():

                if key == "evidence_ids" and isinstance(item, list):

                    value[key] = [
                        evidence_id
                        for evidence_id in item
                        if evidence_id in allowed_evidence_ids
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


# =========================================================
# 어떤 분석기를 사용할지 결정
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

            _analyzer = AzureOpenAIReportAnalyzer()

        else:

            logger.warning(
                "AZURE_OPENAI 설정 없음 - "
                "StubReportAnalyzer 사용"
            )

            _analyzer = StubReportAnalyzer()

    return _analyzer