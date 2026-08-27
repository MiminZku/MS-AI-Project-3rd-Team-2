"""동시통역이 첫 발화 이후로 죽던 문제 회귀 테스트.

Realtime 세션은 턴이 끝나거나 유휴 상태가 되면 서버가 닫는다. 예전에는
클라이언트 객체가 살아 있다는 이유만으로 재연결을 하지 않았고,
send_audio_chunk가 조용히 return 해버려 그 세션 내내 통역이 멈춰 있었다.
"""

import pytest

from app.services.ai import translation
from app.services.ai.realtime_stt import RealtimeSTTClient
from app.services.ai.translation import language_name, translate_text


def _client() -> RealtimeSTTClient:
    async def noop(_text: str) -> None:
        return None

    return RealtimeSTTClient("ses_test", "gpt-realtime-translate", noop, noop)


class _FakeSocket:
    def __init__(self, *, fail_on_send: bool = False) -> None:
        self.sent: list[str] = []
        self.closed = False
        self._fail_on_send = fail_on_send

    async def send(self, payload: str) -> None:
        if self._fail_on_send:
            raise ConnectionError("socket is gone")
        self.sent.append(payload)

    async def close(self) -> None:
        self.closed = True


async def test_연결이_끊기면_살아있지_않다고_보고한다():
    client = _client()
    assert client.is_alive() is False

    client.ws = _FakeSocket()
    client.running = True
    assert client.is_alive() is True

    # 수신 루프가 끝나면 running이 내려간다
    client.running = False
    assert client.is_alive() is False


async def test_끊긴_상태의_오디오는_버려지고_기록된다():
    client = _client()
    client.ws = _FakeSocket()
    client.running = False

    await client.send_audio_chunk("QUJD")

    assert client._dropped_chunks == 1
    assert client.ws.sent == []


async def test_전송_중_끊기면_다음_턴_재연결_대상이_된다():
    client = _client()
    client.ws = _FakeSocket(fail_on_send=True)
    client.running = True

    await client.send_audio_chunk("QUJD")

    # 예외를 삼키되 running을 내려야 ensure_connected가 다시 붙인다
    assert client.is_alive() is False


async def test_ensure_connected는_살아있으면_다시_연결하지_않는다(monkeypatch):
    client = _client()
    client.ws = _FakeSocket()
    client.running = True

    called = False

    async def should_not_run() -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(client, "connect", should_not_run)

    assert await client.ensure_connected() is True
    assert called is False


async def test_ensure_connected는_끊겨_있으면_재연결한다(monkeypatch):
    client = _client()
    old_socket = _FakeSocket()
    client.ws = old_socket
    client.running = False
    client.current_text = "이전 발화 잔여물"

    async def fake_connect() -> None:
        client.ws = _FakeSocket()
        client.running = True

    monkeypatch.setattr(client, "connect", fake_connect)

    assert await client.ensure_connected() is True
    assert client.is_alive() is True
    # 이전 소켓은 정리되고, 이전 발화 텍스트가 새 턴으로 새지 않아야 한다
    assert old_socket.closed is True
    assert client.current_text == ""


async def test_close는_수신_태스크와_소켓을_정리한다():
    import asyncio

    client = _client()
    socket = _FakeSocket()
    client.ws = socket
    client.running = True

    async def forever() -> None:
        await asyncio.sleep(3600)

    client._receive_task = asyncio.create_task(forever())

    await client.close()

    assert client.running is False
    assert client.ws is None
    assert socket.closed is True
    assert client._receive_task is None


# =========================================================
# 통역 폴백
# =========================================================

@pytest.mark.parametrize(
    ("code", "expected"),
    [("en", "English"), ("ko", "Korean"), ("ja", "Japanese"), (None, "English")],
)
def test_언어_코드가_이름으로_변환된다(code, expected):
    assert language_name(code) == expected


async def test_번역기가_없으면_빈_문자열을_돌려준다(monkeypatch):
    """Azure 미설정 시에도 인터뷰가 멈추면 안 된다.

    이 테스트는 "번역기 없음" 상태를 직접 강제해야 한다. 이전에는 ambient
    환경(.env)에 Azure 키가 없다는 사실에 암묵적으로 기대고 있었는데,
    실제로 유효한 키가 채워지자 진짜 Azure를 호출해버렸다(테스트에서
    실제 API 호출이 발생하면 비용도 들고 결과도 환경에 따라 달라진다).
    """
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "azure_openai_endpoint", "")
    monkeypatch.setattr(get_settings(), "azure_openai_api_key", "")
    translation.reset_translator_cache()

    assert await translate_text("안녕하세요") == ""


async def test_빈_텍스트는_번역을_시도하지_않는다():
    translation.reset_translator_cache()
    assert await translate_text("   ") == ""
