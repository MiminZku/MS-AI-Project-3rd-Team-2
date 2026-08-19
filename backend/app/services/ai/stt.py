"""STT 어댑터 (D8, C7).

gpt-live-transcribe vs gpt-transcribe 는 한국어 실측 후 결정한다.
어떤 걸 고르든 라우터/오케스트레이터가 바뀌지 않도록 이 Protocol 뒤에 가둔다.
Azure Speech STT는 사용하지 않는다 (D9 — Speech는 TTS/아바타 전용).

TODO(MVP): Azure Foundry 배포 리전 확인 후 실제 전사 호출 구현.
"""

from __future__ import annotations

import logging
from typing import Protocol

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class Transcriber(Protocol):
    async def transcribe(self, audio: bytes, *, mime_type: str = "audio/webm") -> str:
        """오디오 한 턴을 텍스트로. 턴 기반 순차 파이프라인이므로 파일 단위 전사 (D1)."""
        ...


class NotConfiguredTranscriber:
    """STT 미연결 상태. 프론트가 텍스트 발화를 직접 보내는 데모 모드에서 사용."""

    async def transcribe(self, audio: bytes, *, mime_type: str = "audio/webm") -> str:
        raise NotImplementedError(
            "STT가 아직 연결되지 않았습니다. 데모에서는 utterance 메시지로 텍스트를 직접 전송하세요."
        )


class GptTranscriber:
    """gpt-transcribe / gpt-live-transcribe 어댑터."""

    def __init__(self) -> None:
        from openai import AsyncAzureOpenAI
        settings = get_settings()
        self._model = settings.stt_model
        self._client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )

    async def transcribe(self, audio: bytes, *, mime_type: str = "audio/webm") -> str:
        try:
            # Whisper API expects a tuple (filename, file_content)
            filename = "audio.webm" if "webm" in mime_type else "audio.wav"
            response = await self._client.audio.transcriptions.create(
                model=self._model,
                file=(filename, audio),
                language="ko",
                response_format="text"
            )
            text = str(response).strip()
            logger.info("STT 변환 성공: %s", text)
            return text
        except Exception as e:
            logger.exception("STT 변환 실패")
            raise e


def get_transcriber() -> Transcriber:
    settings = get_settings()
    if settings.use_azure_openai and settings.stt_model:
        return GptTranscriber()
    logger.warning("STT 미설정 — 텍스트 입력 데모 모드로 동작합니다.")
    return NotConfiguredTranscriber()
