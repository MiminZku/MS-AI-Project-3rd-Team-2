"""녹화본 저장 회귀 테스트.

실측 회귀: 인터뷰 종료 시 "녹화 파일 업로드에 실패했습니다"가 뜨고 녹화본이
한 건도 저장되지 않았다. 원인은 `recordings.py`가 참조하는 설정 이름
`azure_storage_recordings_container`가 `Settings`에 정의돼 있지 않아
Blob 업로드 경로에서 AttributeError -> 500 이 난 것이었다.

기존 테스트는 연결 문자열을 비워 로컬 경로만 태웠기 때문에 이 버그를 못 잡았다.
"""

import pytest

from app.core.config import get_settings
from app.services import recordings
from app.services.recordings import RecordingSaveFailed, save_recording

SCRIPT = "1. 요즘 어떤 AI 도구를 쓰시나요?"

# 형식이 올바른 연결 문자열 (실제 계정 아님)
VALID_CONNECTION = (
    "DefaultEndpointsProtocol=https;AccountName=fakeacct;"
    "AccountKey=Zm9vYmFy;EndpointSuffix=core.windows.net"
)


def test_recordings가_참조하는_설정이_모두_정의되어_있다():
    """저장 코드가 읽는 설정 이름이 Settings에 실제로 있어야 한다."""
    settings = get_settings()

    assert hasattr(settings, "azure_storage_connection_string")
    assert hasattr(settings, "azure_storage_recordings_container")
    assert settings.azure_storage_recordings_container


class _FakeBlobClient:
    def __init__(self, store: dict, name: str) -> None:
        self._store = store
        self._name = name
        self.url = f"https://fake.blob.core.windows.net/recordings/{name}"

    def upload_blob(self, content, **_kwargs) -> None:
        self._store[self._name] = content


class _FakeContainer:
    def __init__(self, store: dict, *, fail: bool = False) -> None:
        self._store = store
        self._fail = fail

    def create_container(self) -> None:
        return None

    def get_blob_client(self, name: str):
        if self._fail:
            raise RuntimeError("컨테이너에 접근할 수 없습니다")
        return _FakeBlobClient(self._store, name)


def _patch_azure(monkeypatch, blobs: dict, *, fail: bool = False) -> None:
    """azure-storage-blob SDK를 가짜로 바꿔 Blob 경로를 실제로 태운다."""
    import sys
    import types

    module = types.ModuleType("azure.storage.blob")

    class BlobServiceClient:
        @classmethod
        def from_connection_string(cls, _connection_string):
            return cls()

        def get_container_client(self, _name):
            return _FakeContainer(blobs, fail=fail)

    class ContentSettings:
        def __init__(self, **_kwargs) -> None:
            pass

    module.BlobServiceClient = BlobServiceClient
    module.ContentSettings = ContentSettings
    monkeypatch.setitem(sys.modules, "azure.storage.blob", module)


async def test_Blob_저장_경로가_실제로_동작한다(monkeypatch):
    """설정 이름이 어긋나면 여기서 AttributeError로 잡힌다."""
    blobs: dict = {}
    _patch_azure(monkeypatch, blobs)
    monkeypatch.setattr(get_settings(), "azure_storage_connection_string", VALID_CONNECTION)

    result = await save_recording("ses_test", b"WEBM-BYTES")

    assert blobs["ses_test/recording.webm"] == b"WEBM-BYTES"
    assert result.session_id == "ses_test"
    assert result.size_bytes == len(b"WEBM-BYTES")
    assert result.video_recording_url.startswith("https://")


async def test_Blob_저장에_실패해도_녹화본을_버리지_않는다(monkeypatch):
    """인터뷰는 다시 찍을 수 없다. 로컬에 남기고 경고를 함께 돌려준다."""
    blobs: dict = {}
    _patch_azure(monkeypatch, blobs, fail=True)
    monkeypatch.setattr(get_settings(), "azure_storage_connection_string", VALID_CONNECTION)

    result = await save_recording("ses_fallback", b"WEBM-BYTES")

    assert result.storage == "local"
    assert result.warning and "임시 저장" in result.warning
    assert blobs == {}


async def test_연결_문자열이_잘못되면_형식_문제를_알려준다(monkeypatch):
    """실측 회귀: 값이 ';' 앞에서 잘려 SDK가 거절했고 원인을 알 수 없었다."""
    monkeypatch.setattr(
        get_settings(), "azure_storage_connection_string", "DefaultEndpointsProtocol=https"
    )

    result = await save_recording("ses_badconf", b"WEBM-BYTES")

    assert result.storage == "local"
    assert "AccountName" in (result.warning or "")


def test_연결_문자열_검증기():
    from app.services.recordings import connection_string_problem

    assert connection_string_problem("") is None
    assert connection_string_problem(VALID_CONNECTION) is None
    # 계정 키만 붙여넣은 경우
    assert connection_string_problem("Zm9vYmFy") is not None
    # ';' 에서 잘린 경우
    assert connection_string_problem("DefaultEndpointsProtocol=https") is not None


def test_저장_실패시_502와_사유가_내려간다(client, monkeypatch):
    """맨몸 500이면 대시보드에 '업로드 실패'만 뜨고 원인을 알 수 없다."""

    async def failing(_session_id, _content):
        raise RecordingSaveFailed("스토리지 자격 증명이 올바르지 않습니다")

    monkeypatch.setattr("app.api.routes.sessions.save_recording", failing)

    session_id = client.post(
        "/api/sessions",
        json={"title": "P01", "duration_minutes": 20, "question_script": SCRIPT},
    ).json()["session"]["id"]

    response = client.post(
        f"/api/sessions/{session_id}/recording",
        files={"file": ("r.webm", b"WEBM", "video/webm")},
    )

    assert response.status_code == 502
    assert "스토리지 자격 증명" in response.json()["detail"]


def test_업로드_성공시_세션에_녹화_URL이_남는다(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "azure_storage_connection_string", "")

    session_id = client.post(
        "/api/sessions",
        json={"title": "P01", "duration_minutes": 20, "question_script": SCRIPT},
    ).json()["session"]["id"]

    client.post(
        f"/api/sessions/{session_id}/recording",
        files={"file": ("r.webm", b"WEBM-BYTES", "video/webm")},
    )

    session = client.get(f"/api/sessions/{session_id}").json()["session"]
    assert session["video_recording_url"]

    # 저장된 녹화본을 그대로 다시 받을 수 있어야 한다
    downloaded = client.get(f"/api/sessions/{session_id}/recording/download")
    assert downloaded.status_code == 200
    assert downloaded.content == b"WEBM-BYTES"
