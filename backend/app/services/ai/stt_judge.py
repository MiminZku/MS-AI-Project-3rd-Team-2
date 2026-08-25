"""STT Judge 및 Transcript Validator (D8, Dual-pass STT 검증기).

1차 STT(Azure Speech)와 2차 STT(Whisper/GPT Transcribe)의 결과를
현재 인터뷰 질문 맥락과 대조하여 최적의 전사를 확정하고, 불확실성(Low Confidence)을 판정한다.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Literal
from pydantic import BaseModel, Field

from openai import AsyncAzureOpenAI
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class TranscriptValidationResult(BaseModel):
    selected: str = Field(description="선택된 최종 전사 텍스트")
    status: Literal["accepted", "low_confidence"] = Field(
        description="전사 확정 여부 (accepted: 정상, low_confidence: 재질문 필요)"
    )
    reason: str = Field(default="", description="선택 또는 불신뢰 판정 사유")


class TranscriptValidator:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._deployment = (
            self.settings.azure_openai_timekeeper_deployment
            or self.settings.azure_openai_chat_deployment
            or "gpt-4o-mini"
        )
        self._client: AsyncAzureOpenAI | None = None
        if self.settings.use_azure_openai:
            try:
                self._client = AsyncAzureOpenAI(
                    azure_endpoint=self.settings.azure_openai_endpoint,
                    api_key=self.settings.azure_openai_api_key,
                    api_version=self.settings.azure_openai_api_version,
                    timeout=15.0,
                )
            except Exception as e:
                logger.warning("TranscriptValidator Azure OpenAI 클라이언트 초기화 실패: %s", e)

    async def validate(
        self,
        question_context: str,
        candidate_1: str,
        candidate_2: str,
    ) -> TranscriptValidationResult:
        """1차 및 2차 STT 후보군을 검증하여 최적의 전사를 확정."""
        c1 = candidate_1.strip()
        c2 = candidate_2.strip()

        # 1. 예외 케이스 처리
        if not c1 and not c2:
            return TranscriptValidationResult(
                selected="",
                status="low_confidence",
                reason="두 STT 결과 모두 비어있음",
            )
        if not c1:
            return TranscriptValidationResult(
                selected=c2,
                status="accepted",
                reason="2차 STT 단독 전사 채택",
            )
        if not c2:
            return TranscriptValidationResult(
                selected=c1,
                status="accepted",
                reason="1차 STT 단독 전사 채택",
            )

        # 2. Fast-Path: 공백/특수문자 제외 동일한 경우 (LLM 호출 생략, 0초 지연)
        norm_1 = re.sub(r"[\s\.,\?!~]", "", c1)
        norm_2 = re.sub(r"[\s\.,\?!~]", "", c2)
        if norm_1 == norm_2:
            # 더 길고 온전한 형태를 선택
            selected = c1 if len(c1) >= len(c2) else c2
            return TranscriptValidationResult(
                selected=selected,
                status="accepted",
                reason="1차 및 2차 STT 일치 (Fast-Path)",
            )

        # 3. Azure OpenAI 사용 불가 시 안전 폴백
        if not self._client:
            # 기본적으로 1차(Azure Speech)를 우선하되 더 상세한 텍스트 선택
            selected = c1 if len(c1) >= len(c2) else c2
            return TranscriptValidationResult(
                selected=selected,
                status="accepted",
                reason="오프라인 기본 채택",
            )

        # 4. LLM Judge 호출 (Validation-Path)
        system_prompt = """당신은 실시간 AI 인터뷰의 전사 검증 및 판정기(Transcript Validator / STT Judge)입니다.
진행 중인 인터뷰의 [현재 질문]과 서로 다른 2개의 [STT 후보 텍스트]를 입력받아,
문맥과 발화 흐름에 가장 적합한 최종 전사를 선택하고 신뢰도를 평가하여 JSON으로 반환하세요.

[절대 원칙]
1. ❌ 환각 및 요약 금지: 절대로 새로운 문장을 지어내거나 내용을 해석/요약하지 마세요. 반드시 [후보 1] 또는 [후보 2] 중에서만 더 정확하고 문맥에 맞는 텍스트를 선택해야 합니다.
2. ✅ 신뢰도(status) 판정 기준:
   - "accepted": 두 후보 중 하나가 [현재 질문]의 문맥상 자연스럽고 의미가 통하는 실제 응답자의 발화일 때
   - "low_confidence": 두 후보가 서로 너무 모순되거나, 둘 다 소음/발음 뭉개짐/의미 불명(외계어)으로 무엇을 말했는지 알 수 없을 때

[출력 JSON 형식]
{
  "selected": "선택한 STT 텍스트 (low_confidence인 경우에도 그나마 나은 후보 원문 기재)",
  "status": "accepted" 또는 "low_confidence",
  "reason": "선택 또는 불신뢰 사유 (간결하게)"
}"""

        user_content = f"""[현재 질문]
{question_context or "일반 인터뷰 질문"}

[STT 후보 1 (Azure Speech)]
{c1}

[STT 후보 2 (Whisper STT)]
{c2}"""

        try:
            response = await self._client.chat.completions.create(
                model=self._deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=100,
            )
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            result = TranscriptValidationResult.model_validate(data)
            logger.info(
                "STT Judge 판정 완료: status=%s, selected='%s', reason='%s'",
                result.status,
                result.selected,
                result.reason,
            )
            return result
        except Exception as e:
            logger.warning("STT Judge LLM 호출 실패 (기본 폴백 적용): %s", e)
            # 폴백: 더 긴 후보 채택
            selected = c1 if len(c1) >= len(c2) else c2
            return TranscriptValidationResult(
                selected=selected,
                status="accepted",
                reason=f"Judge 예외로 인한 폴백 채택 ({e})",
            )


_validator: TranscriptValidator | None = None


def get_transcript_validator() -> TranscriptValidator:
    global _validator
    if _validator is None:
        _validator = TranscriptValidator()
    return _validator
