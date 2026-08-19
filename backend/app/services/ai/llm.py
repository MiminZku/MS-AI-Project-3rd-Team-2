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
    """Azure 誘몄뿰寃??곹깭?먯꽌 ?뚯씠?꾨씪?몄쓣 寃利앺븯湲??꾪븳 ?泥?援ы쁽."""

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
                text=f"諛⑷툑 留먯? 以묒뿉 沅곴툑??寃??덈뒗?곗슂, {instruction.text} 愿?⑦빐??議곌툑 ???ㅻ젮二쇱떆寃좎뼱??",
                rationale=f"[STUB] 李멸???吏??'{instruction.text}'瑜??대쾲 ?댁뿉 二쇱엯?덉뒿?덈떎.",
                next_question_index=index,
            )

        if index < len(questions):
            return GeneratedQuestion(
                text=questions[index].text,
                rationale="[STUB] ?湲?以묒씤 李멸???吏?쒓? ?놁뼱 吏덈Ц 由ъ뒪???쒖꽌?濡?吏꾪뻾?덉뒿?덈떎.",
                next_question_index=index + 1,
            )

        return GeneratedQuestion(
            text="?ㅻ뒛 ?댁빞湲고빐二쇱떊 寃?以묒뿉 媛???꾩돩?좊뜕 寃쏀뿕???섎굹留???留먯??댁＜?쒓쿋?댁슂?",
            rationale="[STUB] 吏덈Ц 由ъ뒪?몃? 紐⑤몢 ?뚯쭊??留덈Т由?吏덈Ц?쇰줈 ?꾪솚?덉뒿?덈떎.",
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

