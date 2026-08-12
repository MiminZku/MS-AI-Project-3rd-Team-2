"""다음 질문 생성 + 분기 판단 (§4.2). Azure OpenAI GPT-4o 사용.

키가 없으면 스텁으로 폴백한다. 스텁이어도 '참관자 지시 -> 다음 질문 반영' 흐름은
그대로 관찰되므로, Azure 리소스 없이 CI/CD와 파이프라인을 먼저 검증할 수 있다.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Protocol

from app.core.config import get_settings
from app.schemas.session import Instruction, Session, Turn
from app.services.ai.prompts import build_messages

logger = logging.getLogger(__name__)


@dataclass
class GeneratedQuestion:
    text: str
    rationale: str
    next_question_index: int


class QuestionGenerator(Protocol):
    async def generate(
        self,
        session: Session,
        transcript: list[Turn],
        instruction: Instruction | None,
        timekeeper_hint: str | None = None,
    ) -> GeneratedQuestion: ...


class StubQuestionGenerator:
    """Azure 미연결 상태에서 파이프라인을 검증하기 위한 대체 구현."""

    async def generate(
        self,
        session: Session,
        transcript: list[Turn],
        instruction: Instruction | None,
        timekeeper_hint: str | None = None,
    ) -> GeneratedQuestion:
        index = session.current_question_index
        questions = session.questions

        if instruction is not None:
            return GeneratedQuestion(
                text=f"방금 말씀 중에 궁금한 게 있는데요, {instruction.text} 관련해서 조금 더 들려주시겠어요?",
                rationale=f"[STUB] 참관자 지시 '{instruction.text}'를 이번 턴에 주입했습니다.",
                next_question_index=index,
            )

        if index < len(questions):
            return GeneratedQuestion(
                text=questions[index].text,
                rationale="[STUB] 대기 중인 참관자 지시가 없어 질문 리스트 순서대로 진행했습니다.",
                next_question_index=index + 1,
            )

        return GeneratedQuestion(
            text="오늘 이야기해주신 것 중에 가장 아쉬웠던 경험을 하나만 더 말씀해주시겠어요?",
            rationale="[STUB] 질문 리스트를 모두 소진해 마무리 질문으로 전환했습니다.",
            next_question_index=index,
        )


class AzureOpenAIQuestionGenerator:
    def __init__(self) -> None:
        from openai import AsyncAzureOpenAI  # 스텁 경로에서는 로드하지 않도록 지연 import

        settings = get_settings()
        self._deployment = settings.azure_openai_chat_deployment
        self._client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )

    async def generate(
        self,
        session: Session,
        transcript: list[Turn],
        instruction: Instruction | None,
        timekeeper_hint: str | None = None,
    ) -> GeneratedQuestion:
        messages = build_messages(session, transcript, instruction, timekeeper_hint)
        response = await self._client.chat.completions.create(
            model=self._deployment,
            messages=messages,
            temperature=0.7,
            max_tokens=400,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("GPT 응답 JSON 파싱 실패, 원문을 질문으로 사용: %s", content[:200])
            data = {"question": content.strip()}

        return GeneratedQuestion(
            text=str(data.get("question", "")).strip() or "조금 더 자세히 말씀해주시겠어요?",
            rationale=str(data.get("rationale", "")).strip(),
            next_question_index=int(data.get("next_question_index", session.current_question_index)),
        )


_generator: QuestionGenerator | None = None


def get_question_generator() -> QuestionGenerator:
    global _generator
    if _generator is None:
        if get_settings().use_azure_openai:
            _generator = AzureOpenAIQuestionGenerator()
        else:
            logger.warning("AZURE_OPENAI_* 미설정 — StubQuestionGenerator로 동작합니다.")
            _generator = StubQuestionGenerator()
    return _generator
