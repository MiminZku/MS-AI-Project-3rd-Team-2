"""동시통역 폴백 — 확정된 전사 텍스트를 번역한다.

실시간 통역은 Azure Realtime 웹소켓으로 처리하지만, 그 세션은 턴이 끝나거나
유휴 상태가 되면 서버가 닫는다. 재연결에 실패한 발화에서 백룸이 영어 자막을
아예 못 받는 상황을 막기 위해, 확정된 한국어 전사를 채팅 모델로 번역해 채운다.

실시간 스트리밍처럼 단어 단위로 흐르지는 않지만, 발화가 끝난 시점에 한 번은
반드시 번역이 붙는다.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# 세션에 저장되는 언어 코드 -> 번역 지시에 쓸 언어 이름
_LANGUAGE_NAMES = {
    "ko": "Korean",
    "en": "English",
    "ja": "Japanese",
    "zh": "Chinese",
    "es": "Spanish",
}


def language_name(code: str | None) -> str:
    if not code:
        return "English"
    return _LANGUAGE_NAMES.get(code.lower(), code)


class _AzureTextTranslator:
    def __init__(self) -> None:
        from openai import AsyncAzureOpenAI

        settings = get_settings()
        self._deployment = settings.azure_openai_chat_deployment
        self._client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )

    async def translate(self, text: str, *, target_language: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._deployment,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Translate the user's message into {target_language}. "
                        "Output only the translation — no quotes, no notes, no original text. "
                        "Preserve the speaker's tone and keep it natural for a research interview transcript."
                    ),
                },
                {"role": "user", "content": text},
            ],
            temperature=0,
            max_completion_tokens=500,
        )
        return (response.choices[0].message.content or "").strip()


_translator: _AzureTextTranslator | None = None
_initialized = False


def _get_translator() -> _AzureTextTranslator | None:
    global _translator, _initialized

    if not _initialized:
        _initialized = True
        if get_settings().use_azure_openai:
            try:
                _translator = _AzureTextTranslator()
            except Exception:
                logger.exception("텍스트 번역기 초기화 실패 — 동시통역 폴백이 비활성화됩니다.")
                _translator = None

    return _translator


def reset_translator_cache() -> None:
    """테스트에서 설정을 바꿔 끼울 때 사용."""
    global _translator, _initialized
    _translator = None
    _initialized = False


async def translate_text(text: str, *, target_language: str = "English") -> str:
    """번역 결과. 사용할 수 없거나 실패하면 빈 문자열을 돌려준다 (인터뷰는 계속되어야 한다)."""

    cleaned = (text or "").strip()
    if not cleaned:
        return ""

    translator = _get_translator()
    if translator is None:
        return ""

    try:
        return await translator.translate(cleaned, target_language=target_language)
    except Exception:
        logger.exception("동시통역 폴백 번역 실패")
        return ""


# =========================================================
# 질문 번역 (세션 생성 시 1회)
# =========================================================

# 원문이 이미 대상 언어면 번역하지 않는다.
SOURCE_LANGUAGE_CODE = "ko"


async def translate_questions(
    questions: list[Any],
    *,
    target_language_code: str,
) -> None:
    """질문 트리를 대상 언어로 번역해 각 노드에 채워 넣는다 (제자리 수정).

    참관자(특히 해외 클라이언트)는 지금 무슨 질문을 하는지 알아야 하고,
    인터뷰가 끝난 뒤 기록을 열람·다운로드할 때도 번역이 함께 나가야 한다.
    매번 번역하면 느리고 비싸므로 세션 생성 시 한 번만 번역해 DB에 저장한다.

    번역기를 못 쓰거나 실패해도 세션 생성 자체는 막지 않는다.
    (번역이 없으면 화면에서 원문만 보이며, 인터뷰 진행에는 지장이 없다.)
    """

    if not questions:
        return

    code = (target_language_code or "").lower()
    if not code or code == SOURCE_LANGUAGE_CODE:
        return

    if _get_translator() is None:
        logger.warning("번역기를 사용할 수 없어 질문 번역을 건너뜁니다.")
        return

    target = language_name(code)

    for question in questions:
        question.text_translated = await translate_text(
            question.text,
            target_language=target,
        ) or None

        if not question.branches:
            continue

        translated_branches: dict[str, str] = {}
        for condition, branch_text in question.branches.items():
            translated = await translate_text(branch_text, target_language=target)
            if translated:
                translated_branches[condition] = translated

        question.branches_translated = translated_branches


# =========================================================
# AI 진행자 발화 번역 (인터뷰 중)
# =========================================================

# 번역이 인터뷰 흐름을 붙잡지 않도록 하는 상한(초).
# 넘기면 원문만으로 진행한다 — 참관자 자막이 조금 비는 편이
# 응답자가 아바타 발화를 기다리는 것보다 낫다.
ASSISTANT_TRANSLATION_TIMEOUT_SECONDS = 6.0


async def translate_assistant_text(session: Any, text: str) -> str | None:
    """AI 진행자 발화를 세션의 통역 언어로 번역한다.

    참관자 대시보드에 "지금 무슨 질문 중인지"가 번역돼 보여야 하고,
    인터뷰 종료 후 기록 열람·다운로드에도 함께 나가야 한다.

    세션 생성 시 미리 번역해 둔 질문과 일치하면 그 값을 그대로 쓰고
    (LLM 호출 없음), 아니면 즉석에서 번역한다.
    """
    import asyncio

    cleaned = (text or "").strip()
    if not cleaned:
        return None

    code = (getattr(session, "interpretation_language", "") or "").lower()
    if not code or code == SOURCE_LANGUAGE_CODE:
        return None

    # 빠른 경로: 대본 질문 그대로면 이미 번역해 둔 값이 있다.
    for question in getattr(session, "questions", []) or []:
        if question.text.strip() == cleaned and question.text_translated:
            return question.text_translated
        for condition, branch_text in (question.branches or {}).items():
            if branch_text.strip() == cleaned:
                translated = (question.branches_translated or {}).get(condition)
                if translated:
                    return translated

    try:
        return await asyncio.wait_for(
            translate_text(cleaned, target_language=language_name(code)),
            timeout=ASSISTANT_TRANSLATION_TIMEOUT_SECONDS,
        ) or None
    except asyncio.TimeoutError:
        logger.warning("AI 진행자 발화 번역 시간 초과 — 원문만 전달합니다.")
        return None
    except Exception:
        logger.exception("AI 진행자 발화 번역 실패")
        return None
