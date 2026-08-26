"""리포트 분석용 구조화 출력 호출 (Responses API + Chat Completions 폴백).

리포트 분석기들은 Azure OpenAI **Responses API**(`client.responses.create`)로
JSON Schema 구조화 출력을 받는다. 그런데 이 엔드포인트는 다음 조건이 모두 맞아야 한다:

  - `AZURE_OPENAI_API_VERSION` 이 Responses API를 지원하는 버전일 것
    (`2024-10-21` 같은 GA 버전에는 `/responses` 경로 자체가 없다)
  - 배포된 모델이 Responses API를 지원할 것

하나라도 어긋나면 Azure가 **404 Resource not found** 를 돌려주고, 인터뷰 자체는
`chat.completions` 로 잘 돌아가는데 리포트 생성만 실패한다. 실제로 배포 환경에서
프로젝트 리포트 생성이 이 404로 막혀 있었다.

그래서 Responses 호출이 실패하면 같은 프롬프트를 `chat.completions` 의 JSON 모드로
다시 시도한다. JSON 모드는 오래된 api_version에서도 동작하므로, 인터뷰가 돌아가는
환경이면 리포트도 반드시 돌아간다.
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


async def create_structured_json(
    client: Any,
    *,
    deployment: str,
    system_prompt: str,
    user_input: str,
    schema_name: str,
    schema: dict[str, Any],
    max_output_tokens: int,
) -> str:
    """스키마를 따르는 JSON 문자열을 돌려준다.

    Responses API를 먼저 시도하고, 그 엔드포인트를 쓸 수 없으면
    Chat Completions JSON 모드로 폴백한다.
    """

    try:
        response = await client.responses.create(
            model=deployment,
            instructions=system_prompt,
            input=user_input,
            reasoning={"effort": "none"},
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
    # 폴백: Chat Completions JSON 모드
    #
    # json_schema 강제는 api_version을 타므로, 스키마를 프롬프트에 실어 보내고
    # 어느 버전에서나 되는 json_object 모드를 쓴다.
    # -----------------------------------------------------

    schema_instruction = (
        f"{system_prompt}\n\n"
        "반드시 아래 JSON Schema를 그대로 만족하는 JSON 객체 하나만 출력하라. "
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
        temperature=0,
        max_completion_tokens=max_output_tokens,
        response_format={"type": "json_object"},
    )

    return completion.choices[0].message.content or ""
