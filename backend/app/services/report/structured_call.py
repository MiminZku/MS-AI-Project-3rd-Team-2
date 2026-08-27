"""리포트 분석용 구조화 출력 호출 (Responses API + Chat Completions 폴백).

리포트 분석기들은 Azure OpenAI **Responses API**(`client.responses.create`)로
JSON Schema 구조화 출력을 받는다. 그런데 이 엔드포인트는 다음 조건이 모두 맞아야 한다:

  - `AZURE_OPENAI_API_VERSION` 이 Responses API를 지원하는 버전일 것
    (`2024-10-21` 같은 GA 버전에는 `/responses` 경로 자체가 없다)
  - 배포된 모델이 Responses API를 지원할 것

하나라도 어긋나면 Azure가 **404 Resource not found** 를 돌려주고, 인터뷰 자체는
`chat.completions` 로 잘 돌아가는데 리포트 생성만 실패한다. 실제로 배포 환경에서
프로젝트 리포트 생성이 이 404로 막혀 있었다.

그래서 아래 3단으로 내려간다:

  1. Responses API                              (가장 좋음)
  2. chat.completions + json_schema (strict)    <- 서버가 스키마를 강제
  3. chat.completions + json_object             (최후 수단, 스키마 강제 없음)

2단이 중요하다. 3단(json_object)은 "JSON을 뱉어라"까지만 강제하고 스키마는
전혀 강제하지 않아서, 섹션이 12개인 종합 리포트에서 모델이 앞부분만 만들고 멈춘
유효한 JSON을 내놓는 일이 실제로 있었다. 그 결과가
"8 validation errors for StudyReportAnalysis ... Field required" 였다.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _looks_like_missing_endpoint(error: Exception) -> bool:
    """Responses API를 못 쓰는 상황인지 (404 / 미지원 경로) 판별한다."""
    status = getattr(error, "status_code", None)
    if status in (404, 400):
        return True

    message = str(error).lower()
    return (
        "404" in message
        or "resource not found" in message
        or "unrecognized request argument" in message
        or "unknown parameter" in message
        or "does not support" in message
    )


def _looks_like_unsupported_response_format(error: Exception) -> bool:
    """이 배포/api_version이 json_schema(Structured Outputs)를 못 쓰는지 판별한다."""
    status = getattr(error, "status_code", None)
    message = str(error).lower()

    if status in (400, 404):
        return True

    return (
        "response_format" in message
        or "json_schema" in message
        or "unsupported" in message
        or "invalid_request_error" in message
        or "unknown parameter" in message
    )


async def create_structured_json(
    client: Any,
    *,
    deployment: str,
    system_prompt: str,
    user_input: str,
    schema_name: str,
    schema: dict[str, Any],
    max_output_tokens: int,
    temperature: float = 0,
) -> str:
    """스키마를 따르는 JSON 문자열을 돌려준다.

    Responses API -> chat.completions(json_schema) -> chat.completions(json_object)
    순으로 내려가며, 쓸 수 있는 가장 강한 스키마 강제 수단을 고른다.
    """

    try:
        response = await client.responses.create(
            model=deployment,
            instructions=system_prompt,
            input=user_input,
            reasoning={"effort": "none"},
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            text={
                "verbosity": "low",
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                },
            },
        )
        return response.output_text or ""

    except Exception as error:
        if not _looks_like_missing_endpoint(error):
            raise

        logger.warning(
            "Responses API를 사용할 수 없어 chat.completions JSON 모드로 폴백합니다 "
            "(deployment=%s): %s",
            deployment,
            error,
        )

    # -----------------------------------------------------
    # 폴백 1: Chat Completions + Structured Outputs (json_schema)
    #
    # 이게 핵심이다. json_object 모드는 "JSON을 뱉어라"까지만 강제하고
    # 스키마는 전혀 강제하지 않는다. 실제로 섹션이 12개인 종합 리포트 스키마에서
    # 모델이 앞쪽 4개 섹션만 만들고 멈춘 "유효한" JSON을 내놓아
    # "8 validation errors ... Field required" 로 리포트 생성이 실패했다.
    # 온도를 올려 재시도해도 지시 이행 능력 문제라 해결되지 않는다.
    #
    # json_schema + strict 는 서버가 스키마를 강제하므로 필드가 빠질 수 없다.
    # -----------------------------------------------------

    try:
        completion = await client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            temperature=temperature,
            max_completion_tokens=max_output_tokens,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                },
            },
        )
        return completion.choices[0].message.content or ""

    except Exception as error:
        if not _looks_like_unsupported_response_format(error):
            raise

        logger.warning(
            "Structured Outputs(json_schema)를 사용할 수 없어 json_object 모드로 "
            "폴백합니다 (deployment=%s): %s",
            deployment,
            error,
        )

    # -----------------------------------------------------
    # 폴백 2: Chat Completions JSON 모드 (최후 수단)
    #
    # 스키마 강제가 안 되므로 프롬프트에 스키마를 실어 보내고 기대할 수밖에 없다.
    # 필드 누락 가능성이 남아 있어, 호출자가 검증 후 재시도한다.
    # -----------------------------------------------------

    schema_instruction = (
        f"{system_prompt}\n\n"
        "반드시 아래 JSON Schema를 그대로 만족하는 JSON 객체 하나만 출력하라. "
        "스키마의 최상위 키를 하나도 빠뜨리지 마라. "
        "설명, 주석, 코드펜스를 절대 붙이지 마라.\n\n"
        f"[JSON Schema: {schema_name}]\n"
        f"{json.dumps(schema, ensure_ascii=False)}"
    )

    completion = await client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": schema_instruction},
            {"role": "user", "content": user_input},
        ],
        temperature=temperature,
        max_completion_tokens=max_output_tokens,
        response_format={"type": "json_object"},
    )

    return completion.choices[0].message.content or ""
