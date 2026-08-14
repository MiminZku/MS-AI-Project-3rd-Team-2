from __future__ import annotations

import json
import logging
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.core.config import get_settings
from app.schemas.session import QuestionNode
from app.schemas.study import InformationSlot

logger = logging.getLogger(__name__)


# =========================================================
# GPT 출력 전용 Strict Schema
# =========================================================

class GeneratedSlot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot_id: str
    question_id: str
    slot_name: str
    description: str

    importance: Literal[
        "high",
        "medium",
        "low",
    ]


class SlotGenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    information_slots: list[GeneratedSlot]


# =========================================================
# Slot Generator
# =========================================================

class SlotGenerator:

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


    async def generate(
        self,
        title: str,
        research_purpose: str,
        question_script: str,
        questions: list[QuestionNode],
    ) -> list[InformationSlot]:

        # -------------------------------------------------
        # 실제 존재하는 Question ID
        # -------------------------------------------------

        allowed_question_ids = {
            question.id
            for question in questions
        }

        question_data = [
            {
                "question_id": question.id,
                "order": question.order,
                "question": question.text,
            }
            for question in questions
        ]


        # -------------------------------------------------
        # Prompt
        # -------------------------------------------------

        system_prompt = """
당신은 기업 시장조사 및 UX Research 전문 연구 설계자입니다.

기업이 입력한 조사 목적과 Moderator Guide를 분석하여
인터뷰에서 반드시 확보해야 하는 Information Slot을 설계하세요.


==================================================
[Information Slot이란]
==================================================

Information Slot은 단순한 질문 목록이 아닙니다.

각 질문을 통해 연구자가 실제로 알고 싶어 하는
'정보 단위'입니다.

예를 들어 질문이

"현재 어떤 AI 도구를 사용하고 있으며
상황에 따라 어떻게 다르게 사용하나요?"

라면 Information Slot은 다음처럼 나뉠 수 있습니다.

- current_tool_stack
- task_based_tool_choice


질문이

"왜 A보다 B를 선호하나요?"

라면 다음처럼 나뉠 수 있습니다.

- preference_reason
- workflow_experience
- concrete_example


==================================================
[생성 원칙]
==================================================

1. 조사 목적과 질문지에 실제로 필요한 Slot만 생성하세요.

2. 질문에 없는 전혀 새로운 조사 주제를
임의로 확장하지 마세요.

3. 하나의 질문에서 여러 종류의 정보를
확보해야 한다면 Slot을 여러 개 생성할 수 있습니다.

4. 서로 의미가 거의 같은 Slot은 중복 생성하지 마세요.

5. slot_id는 짧고 의미 있는 영어 snake_case로 작성하세요.

예:
current_tool_stack
preference_reason
switching_trigger
cost_impact

6. question_id는 입력으로 제공된 실제 Question ID만
사용할 수 있습니다.

7. slot_name은 연구자가 화면에서 바로 이해할 수 있도록
한국어로 작성하세요.

8. description은
'이 Slot에서 실제로 무엇을 확인해야 하는지'
명확하게 작성하세요.


==================================================
[Importance]
==================================================

importance는 다음 중 하나입니다.

high
medium
low


high:
조사 목적 달성을 위해 반드시 확보해야 하는 핵심 정보

medium:
중요하지만 핵심 결과를 판단하는 데 절대적이지 않은 정보

low:
보조적으로 확보하면 좋은 정보


질문의 순서가 앞이라고 해서
importance를 높게 주면 안 됩니다.

조사 목적과의 관계를 기준으로 판단하세요.


==================================================
[중요]
==================================================

Moderator 질문에 포함된 주장이나 가정은
참가자의 실제 의견이 아닙니다.

이 단계에서는 참가자 답변을 분석하는 것이 아니라,
'앞으로 인터뷰에서 어떤 정보를 확보해야 하는가'를
설계하는 것입니다.


==================================================
[출력]
==================================================

제공된 JSON Schema를 정확하게 따르세요.

Schema에 없는 필드를 만들지 마세요.

필수 필드를 누락하지 마세요.
"""

        input_data = {
            "research_title": title,
            "research_purpose": research_purpose,
            "original_question_script": question_script,
            "questions": question_data,
        }


        # -------------------------------------------------
        # Structured Output Schema
        # -------------------------------------------------

        output_schema = (
            SlotGenerationResult
            .model_json_schema()
        )


        # -------------------------------------------------
        # GPT-5.1 호출
        # -------------------------------------------------

        try:
            response = await self._client.responses.create(
                model=self._deployment,

                instructions=system_prompt,

                input=(
                    "아래 조사 목적과 질문지를 분석하고 "
                    "Information Slot을 설계하세요.\n\n"
                    + json.dumps(
                        input_data,
                        ensure_ascii=False,
                        indent=2,
                    )
                ),

                reasoning={
                    "effort": "none"
                },

                max_output_tokens=5000,

                text={
                    "verbosity": "low",

                    "format": {
                        "type": "json_schema",
                        "name": "information_slot_generation",
                        "schema": output_schema,
                        "strict": True,
                    },
                },
            )

        except Exception:
            logger.exception(
                "Information Slot 생성 실패"
            )
            raise


        # -------------------------------------------------
        # 응답 확인
        # -------------------------------------------------

        content = response.output_text

        if not content:
            raise ValueError(
                "Azure OpenAI가 빈 Slot 결과를 반환했습니다."
            )


        # -------------------------------------------------
        # JSON → Pydantic
        # -------------------------------------------------

        raw_result = json.loads(content)

        validated = (
            SlotGenerationResult
            .model_validate(raw_result)
        )


        # -------------------------------------------------
        # Question ID 검증 + 중복 Slot 검증
        # -------------------------------------------------

        seen_slot_ids: set[str] = set()

        final_slots: list[InformationSlot] = []

        for generated in validated.information_slots:

            if (
                generated.question_id
                not in allowed_question_ids
            ):
                raise ValueError(
                    "존재하지 않는 question_id가 "
                    f"Slot에 포함됨: {generated.question_id}"
                )

            if generated.slot_id in seen_slot_ids:
                raise ValueError(
                    "중복 Slot ID가 생성됨: "
                    f"{generated.slot_id}"
                )

            seen_slot_ids.add(
                generated.slot_id
            )

            final_slots.append(
                InformationSlot(
                    slot_id=generated.slot_id,
                    question_id=generated.question_id,
                    slot_name=generated.slot_name,
                    description=generated.description,
                    importance=generated.importance,
                )
            )


        if not final_slots:
            raise ValueError(
                "생성된 Information Slot이 없습니다."
            )

        return final_slots


# =========================================================
# Singleton
# =========================================================

_slot_generator: SlotGenerator | None = None


def get_slot_generator() -> SlotGenerator:

    global _slot_generator

    if _slot_generator is None:
        _slot_generator = SlotGenerator()

    return _slot_generator