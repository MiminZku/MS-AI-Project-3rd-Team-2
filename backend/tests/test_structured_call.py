"""Responses API를 못 쓰는 환경에서도 리포트 분석이 돌아가야 한다.

실측 회귀: 배포 환경에서 프로젝트 리포트 생성이
`Error code: 404 - {'error': {'code': '404', 'message': 'Resource not found'}}`
로 실패했다. 인터뷰는 chat.completions 로 잘 돌아가는데, 리포트 분석기만
`client.responses.create` (Responses API)를 써서 그 엔드포인트가 없는
api_version/배포에서 404가 났다.
"""

import pytest

from app.services.report.structured_call import create_structured_json

SCHEMA = {"type": "object", "properties": {"summary": {"type": "string"}}}


class _NotFound(Exception):
    def __init__(self) -> None:
        super().__init__(
            "Error code: 404 - {'error': {'code': '404', 'message': 'Resource not found'}}"
        )
        self.status_code = 404


class _Responses:
    def __init__(self, *, error: Exception | None, output: str = "") -> None:
        self._error = error
        self._output = output
        self.called = False

    async def create(self, **_kwargs):
        self.called = True
        if self._error:
            raise self._error
        return type("R", (), {"output_text": self._output})()


class _ChatCompletions:
    def __init__(self, output: str = '{"summary": "폴백 결과"}') -> None:
        self._output = output
        self.called = False
        self.kwargs: dict = {}

    async def create(self, **kwargs):
        self.called = True
        self.kwargs = kwargs
        message = type("M", (), {"content": self._output})()
        choice = type("C", (), {"message": message})()
        return type("Resp", (), {"choices": [choice]})()


class _FakeClient:
    def __init__(self, *, responses_error: Exception | None = None, responses_output: str = "") -> None:
        self.responses = _Responses(error=responses_error, output=responses_output)
        self._completions = _ChatCompletions()
        self.chat = type("Chat", (), {"completions": self._completions})()

    @property
    def completions(self) -> _ChatCompletions:
        return self._completions


async def _call(client: _FakeClient) -> str:
    return await create_structured_json(
        client,
        deployment="gpt-4o",
        system_prompt="분석하라",
        user_input="{}",
        schema_name="analysis",
        schema=SCHEMA,
        max_output_tokens=1000,
    )


async def test_Responses_API가_되면_그대로_쓴다():
    client = _FakeClient(responses_output='{"summary": "정상"}')

    result = await _call(client)

    assert result == '{"summary": "정상"}'
    assert client.completions.called is False


async def test_Responses가_404면_chat_completions로_폴백한다():
    client = _FakeClient(responses_error=_NotFound())

    result = await _call(client)

    assert result == '{"summary": "폴백 결과"}'
    assert client.responses.called is True
    assert client.completions.called is True


async def test_폴백_호출에_스키마와_JSON모드가_들어간다():
    client = _FakeClient(responses_error=_NotFound())

    await _call(client)

    kwargs = client.completions.kwargs
    assert kwargs["response_format"] == {"type": "json_object"}
    # 스키마를 강제할 수 없는 모드이므로 프롬프트에 스키마를 실어 보낸다
    system_prompt = kwargs["messages"][0]["content"]
    assert "JSON Schema" in system_prompt
    assert "summary" in system_prompt


@pytest.mark.parametrize(
    "message",
    [
        "Error code: 404 - Resource not found",
        "Unrecognized request argument supplied: reasoning",
        "This model does not support the responses endpoint",
    ],
)
async def test_엔드포인트_미지원_신호를_폴백으로_처리한다(message: str):
    client = _FakeClient(responses_error=RuntimeError(message))

    result = await _call(client)

    assert result == '{"summary": "폴백 결과"}'


async def test_그_외의_오류는_그대로_올린다():
    """레이트리밋·인증 오류까지 폴백으로 삼키면 원인이 가려진다."""
    client = _FakeClient(responses_error=RuntimeError("429 rate limit exceeded"))

    with pytest.raises(RuntimeError, match="429"):
        await _call(client)

    assert client.completions.called is False
