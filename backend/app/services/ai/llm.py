"""?ㅼ쓬 吏덈Ц ?앹꽦 + 遺꾧린 ?먮떒 (짠4.2). Azure OpenAI GPT-4o ?ъ슜.

?ㅺ? ?놁쑝硫??ㅽ뀅?쇰줈 ?대갚?쒕떎. ?ㅽ뀅?댁뼱??'李멸???吏??-> ?ㅼ쓬 吏덈Ц 諛섏쁺' ?먮쫫?
洹몃?濡?愿李곕릺誘濡? Azure 由ъ냼???놁씠 CI/CD? ?뚯씠?꾨씪?몄쓣 癒쇱? 寃利앺븷 ???덈떎.
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
    """Azure 미연결 상태에서 파이프라인을 검증하기 위한 스텁 구현."""

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
                text=f"방금 말씀 중에 궁금한 점이 있는데요, {instruction.text} 관련해서 조금 더 들려주시겠어요?",
                rationale=f"[STUB] 참관자 지시 '{instruction.text}'를 이번 턴에 주입했습니다.",
                next_question_index=index,
            )

        # 직전 답변에 분기(Branch) 키워드가 매칭되는지 확인
        last_turn = transcript[-1] if transcript else None
        if last_turn and last_turn.speaker == "interviewee" and index < len(questions):
            curr_q = questions[index]
            for branch_k, branch_q in curr_q.branches.items():
                if branch_k in last_turn.text:
                    return GeneratedQuestion(
                        text=branch_q,
                        rationale=f"[STUB] 응답자의 키워드 '{branch_k}'에 매칭되어 파생 꼬리질문으로 전이했습니다.",
                        next_question_index=index + 1,
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
        from openai import AsyncAzureOpenAI  # ?ㅽ뀅 寃쎈줈?먯꽌??濡쒕뱶?섏? ?딅룄濡?吏??import

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
            max_completion_tokens=1300,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("GPT ?묐떟 JSON ?뚯떛 ?ㅽ뙣, ?먮Ц??吏덈Ц?쇰줈 ?ъ슜: %s", content[:200])
            data = {"question": content.strip()}

        return GeneratedQuestion(
            text=str(data.get("question", "")).strip() or "議곌툑 ???먯꽭??留먯??댁＜?쒓쿋?댁슂?",
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
            logger.warning("AZURE_OPENAI_* 誘몄꽕????StubQuestionGenerator濡??숈옉?⑸땲??")
            _generator = StubQuestionGenerator()
    return _generator

