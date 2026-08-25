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
            logger.warning("Azure OpenAI Whisper STT (%s) 실패: %s", self._model, e)
            try:
                # 일반적인 whisper 모델명으로 다시 한번 시도
                fallback_model = "whisper" if self._model != "whisper" else "whisper-1"
                response = await self._client.audio.transcriptions.create(
                    model=fallback_model,
                    file=("audio.wav", audio),
                    language="ko",
                    response_format="text",
                )
                text = str(response).strip()
                logger.info("Azure OpenAI Whisper STT (%s 폴백) 성공: %s", fallback_model, text)
                return text
            except Exception as e2:
                logger.warning("Azure OpenAI Whisper STT (폴백 %s) 실패: %s", fallback_model, e2)
                return ""


import asyncio
from app.services.ai.stt_judge import TranscriptValidationResult, get_transcript_validator


class DualPassTranscriber:
    """1차 Azure Speech + 2차 Whisper 동시 실행 및 LLM Validator(STT Judge) 검증 트랜스크라이버."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.speech_transcriber = None
        self.gpt_transcriber = None
        self.validator = get_transcript_validator()

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
        """기존 단일 인터페이스 호환."""
        res = await self.transcribe_dual_pass(audio, question_context="", mime_type=mime_type)
        return res.selected

    async def transcribe_dual_pass(
        self,
        audio: bytes,
        *,
        question_context: str = "",
        mime_type: str = "audio/wav"
    ) -> TranscriptValidationResult:
        """1차 & 2차 STT 병렬 실행 후 STT Judge로 최적의 전사 및 신뢰도 확정."""
        tasks = []
        if self.speech_transcriber:
            tasks.append(self.speech_transcriber.transcribe(audio, mime_type=mime_type))
        else:
            tasks.append(asyncio.sleep(0, result=""))

        if self.gpt_transcriber:
            tasks.append(self.gpt_transcriber.transcribe(audio, mime_type=mime_type))
        else:
            tasks.append(asyncio.sleep(0, result=""))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        c1 = results[0] if isinstance(results[0], str) else ""
        c2 = results[1] if isinstance(results[1], str) else ""

        return await self.validator.validate(question_context, c1, c2)


class CompositeTranscriber(DualPassTranscriber):
    """기존 클래스명 호환."""
    pass


def get_transcriber() -> DualPassTranscriber:
    return DualPassTranscriber()


