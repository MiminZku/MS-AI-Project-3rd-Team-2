"""TTS / TTS Avatar 어댑터 (D7, D9, C6).

기본은 Azure Speech TTS Avatar(실사풍). 리전/역량 문제로 막히면 오브(파형) 폴백으로
내려가야 하므로 두 경로를 같은 인터페이스 뒤에 둔다.

MVP 구현 순서:
  1) 일반 TTS 음성 합성 (오브 폴백에서 그대로 재사용)
  2) TTS Avatar 실시간 스트리밍 (프론트가 WebRTC로 수신)
문장 단위 청크 스트리밍을 적용해 체감 지연을 줄일 것 (C3).
"""

from __future__ import annotations

import logging
from typing import Literal, Protocol

from app.core.config import get_settings

logger = logging.getLogger(__name__)

SpeechMode = Literal["avatar", "orb"]


class SpeechSynthesizer(Protocol):
    async def synthesize(self, text: str, *, voice: str = "ko-KR-SunHiNeural") -> bytes:
        """텍스트 -> 오디오 바이트."""
        ...


class NotConfiguredSynthesizer:
    """AZURE_SPEECH_* 미설정. 프론트가 브라우저 TTS 또는 자막으로 대체."""

    async def synthesize(self, text: str, *, voice: str = "ko-KR-SunHiNeural") -> bytes:
        raise NotImplementedError("AZURE_SPEECH_KEY / AZURE_SPEECH_REGION이 설정되지 않았습니다.")


class AzureSpeechSynthesizer:
    def __init__(self) -> None:
        settings = get_settings()
        self._key = settings.azure_speech_key
        self._region = settings.azure_speech_region

    async def synthesize(self, text: str, *, voice: str = "ko-KR-SunHiNeural") -> bytes:
        # TODO(MVP): Speech REST /cognitiveservices/v1 호출 또는 SDK 스트리밍 합성
        raise NotImplementedError("Azure Speech TTS 호출 구현 필요")


def get_synthesizer() -> SpeechSynthesizer:
    settings = get_settings()
    if settings.azure_speech_key and settings.azure_speech_region:
        return AzureSpeechSynthesizer()
    logger.warning("Azure Speech 미설정 — 프론트 폴백(자막/브라우저 TTS)으로 진행합니다.")
    return NotConfiguredSynthesizer()
