"""STT 어댑터 (D8, C7).

gpt-live-transcribe vs gpt-transcribe 는 한국어 실측 후 결정한다.
어떤 걸 고르든 라우터/오케스트레이터가 바뀌지 않도록 이 Protocol 뒤에 가둔다.
Azure Speech STT는 사용하지 않는다 (D9 — Speech는 TTS/아바타 전용).

TODO(MVP): Azure Foundry 배포 리전 확인 후 실제 전사 호출 구현.
"""

from __future__ import annotations

import logging
from typing import Protocol

import httpx
from openai import AsyncAzureOpenAI
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class Transcriber(Protocol):
    async def transcribe(self, audio: bytes, *, mime_type: str = "audio/wav") -> str:
        """오디오 한 턴을 텍스트로 변환."""
        ...


class AzureSpeechRestTranscriber:
    """Azure AI Speech REST STT 어댑터 (별도 모델 배포 없이 Region/Key로 고속 한국어 인식)."""

    def __init__(self, key: str, region: str) -> None:
        self.key = key
        self.region = region

    async def transcribe(self, audio: bytes, *, mime_type: str = "audio/wav") -> str:
        url = f"https://{self.region}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language=ko-KR"
        headers = {
            "Ocp-Apim-Subscription-Key": self.key,
            "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=24000",
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, headers=headers, content=audio)
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("RecognitionStatus")
                    if status == "Success":
                        text = data.get("DisplayText", "").strip()
                        logger.info("Azure Speech REST STT 성공: %s", text)
                        return text
                    logger.info("Azure Speech 인식 결과: %s", status)
        except Exception as e:
            logger.warning("Azure Speech REST STT 요청 실패: %s", e)
        return ""


class GptTranscriber:
    """Azure OpenAI Whisper STT 어댑터."""

    def __init__(self) -> None:
        settings = get_settings()
        self._model = settings.stt_model or "whisper"
        self._client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )

    async def transcribe(self, audio: bytes, *, mime_type: str = "audio/wav") -> str:
        try:
            filename = "audio.wav"
            response = await self._client.audio.transcriptions.create(
                model=self._model,
                file=(filename, audio),
                language="ko",
                response_format="text",
            )
            text = str(response).strip()
            logger.info("Azure OpenAI Whisper STT 성공: %s", text)
            return text
        except Exception as e:
            logger.warning("Azure OpenAI Whisper STT 실패: %s", e)
            return ""


class CompositeTranscriber:
    """Azure Speech ➡️ Whisper 순차 폴백 지원 트랜스크라이버."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.speech_transcriber = None
        self.gpt_transcriber = None

        if self.settings.azure_speech_key and self.settings.azure_speech_region:
            self.speech_transcriber = AzureSpeechRestTranscriber(
                self.settings.azure_speech_key, self.settings.azure_speech_region
            )
        if self.settings.use_azure_openai:
            try:
                self.gpt_transcriber = GptTranscriber()
            except Exception as e:
                logger.warning(f"GptTranscriber 초기화 실패: {e}")

    async def transcribe(self, audio: bytes, *, mime_type: str = "audio/wav") -> str:
        if self.speech_transcriber:
            text = await self.speech_transcriber.transcribe(audio, mime_type=mime_type)
            if text:
                return text
        if self.gpt_transcriber:
            text = await self.gpt_transcriber.transcribe(audio, mime_type=mime_type)
            if text:
                return text
        return ""


def get_transcriber() -> Transcriber:
    return CompositeTranscriber()

