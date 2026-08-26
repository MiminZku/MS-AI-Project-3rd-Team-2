"""동시통역 폴백 — 확정된 전사 텍스트를 번역한다.

실시간 통역은 Azure Realtime 웹소켓으로 처리하지만, 그 세션은 턴이 끝나거나
유휴 상태가 되면 서버가 닫는다. 재연결에 실패한 발화에서 백룸이 영어 자막을
아예 못 받는 상황을 막기 위해, 확정된 한국어 전사를 채팅 모델로 번역해 채운다.

실시간 스트리밍처럼 단어 단위로 흐르지는 않지만, 발화가 끝난 시점에 한 번은
반드시 번역이 붙는다.
"""

from __future__ import annotations

import logging

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
