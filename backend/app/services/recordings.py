"""Persistence for browser-recorded interview media."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from pydantic import BaseModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)


LOCAL_RECORDINGS_DIR = Path(__file__).resolve().parents[2] / "data" / "recordings"


class RecordingUploadResponse(BaseModel):
    session_id: str
    video_recording_url: str
    size_bytes: int
    status: str = "uploaded"
    # "blob" | "local". Blob 설정이 잘못돼 로컬로 저장된 경우를 구분한다.
    storage: str = "local"
    # 저장은 됐지만 짚고 넘어가야 할 문제가 있을 때 (예: Blob 설정 오류로 임시 저장)
    warning: str | None = None


# Azure Storage 연결 문자열에 반드시 들어가야 하는 항목.
# 계정 키만 붙여넣거나, Container Apps 환경변수를 따옴표 없이 넣어 ';' 앞에서
# 잘린 값이 들어오면 SDK가 "Connection string missing required connection details"로
# 거절한다. 인터뷰가 끝난 뒤에야 알게 되지 않도록 미리 확인한다.
_REQUIRED_CONNECTION_PARTS = ("AccountName=", "AccountKey=")


def connection_string_problem(connection_string: str) -> str | None:
    """연결 문자열이 쓸 수 없는 형태면 사람이 읽을 수 있는 사유를 돌려준다."""
    if not connection_string:
        return None  # 미설정은 로컬 저장을 의도한 것으로 본다

    missing = [part for part in _REQUIRED_CONNECTION_PARTS if part not in connection_string]
    if missing:
        return (
            "AZURE_STORAGE_CONNECTION_STRING 값에 "
            + ", ".join(part.rstrip("=") for part in missing)
            + " 가 없습니다. Azure Portal > 스토리지 계정 > 액세스 키의 '연결 문자열'을 "
            "통째로(DefaultEndpointsProtocol=...;AccountName=...;AccountKey=...;EndpointSuffix=...) "
            "따옴표로 감싸서 넣어야 합니다. ';' 때문에 값이 잘리지 않았는지 확인하세요."
        )
    return None


class RecordingNotFound(Exception):
    """세션에 저장된 녹화본이 없거나 스토리지에서 찾을 수 없다."""


async def load_recording(session_id: str, video_recording_url: str | None) -> bytes:
    """녹화본 바이트를 읽어온다.

    로컬 저장과 Azure Blob 두 경로를 모두 지원한다. Blob은 컨테이너 공개 여부에
    상관없이 받을 수 있도록 백엔드가 자격 증명으로 직접 내려받아 전달한다.
    """
    if not video_recording_url:
        raise RecordingNotFound("녹화본이 없습니다.")

    if video_recording_url.startswith("/recordings/"):
        path = LOCAL_RECORDINGS_DIR / session_id / "recording.webm"
        if not path.exists():
            raise RecordingNotFound("녹화 파일을 찾을 수 없습니다.")
        return await asyncio.to_thread(path.read_bytes)

    settings = get_settings()
    if not settings.azure_storage_connection_string:
        raise RecordingNotFound("녹화 스토리지에 접근할 수 없습니다.")

    return await asyncio.to_thread(_download_from_azure, session_id)


def _download_from_azure(session_id: str) -> bytes:
    from azure.storage.blob import BlobServiceClient

    settings = get_settings()
    blob_service = BlobServiceClient.from_connection_string(settings.azure_storage_connection_string)
    container = blob_service.get_container_client(settings.azure_storage_recordings_container)
    blob_client = container.get_blob_client(f"{session_id}/recording.webm")

    try:
        return blob_client.download_blob().readall()
    except Exception as exc:  # noqa: BLE001 - SDK 예외 종류가 다양해 한 번에 처리한다
        raise RecordingNotFound("녹화 파일을 내려받지 못했습니다.") from exc


class RecordingSaveFailed(Exception):
    """녹화본을 저장하지 못했다."""


async def save_recording(session_id: str, content: bytes) -> RecordingUploadResponse:
    """Save an interview recording to Azure Blob Storage or the local fallback.

    Blob 저장이 실패해도 녹화본을 버리지 않는다. 인터뷰는 다시 찍을 수 없으므로
    일단 로컬에 남겨 내려받을 수 있게 하고, 설정을 고쳐야 한다는 경고를 함께 돌려준다.
    (컨테이너가 재시작되면 로컬 파일은 사라지므로 어디까지나 임시 안전망이다.)
    """
    settings = get_settings()
    connection_string = settings.azure_storage_connection_string

    if not connection_string:
        return await asyncio.to_thread(_save_locally, session_id, content)

    problem = connection_string_problem(connection_string)
    if problem:
        logger.error("Blob Storage 설정 오류 session=%s: %s", session_id, problem)
        return await _save_locally_with_warning(session_id, content, problem)

    try:
        return await asyncio.to_thread(_save_to_azure, session_id, content)
    except Exception as error:
        logger.exception("Blob Storage 녹화 업로드 실패 session=%s", session_id)
        return await _save_locally_with_warning(
            session_id,
            content,
            f"Blob Storage 업로드에 실패해 서버에 임시 저장했습니다: {error}",
        )


async def _save_locally_with_warning(
    session_id: str,
    content: bytes,
    warning: str,
) -> RecordingUploadResponse:
    try:
        result = await asyncio.to_thread(_save_locally, session_id, content)
    except Exception as error:
        logger.exception("녹화본 로컬 임시 저장까지 실패 session=%s", session_id)
        raise RecordingSaveFailed(f"{warning} (임시 저장도 실패: {error})") from error

    result.warning = f"{warning} 지금 받아두지 않으면 서버 재시작 시 사라질 수 있습니다."
    return result


def _save_locally(session_id: str, content: bytes) -> RecordingUploadResponse:
    recording_path = LOCAL_RECORDINGS_DIR / session_id / "recording.webm"
    recording_path.parent.mkdir(parents=True, exist_ok=True)
    recording_path.write_bytes(content)
    return RecordingUploadResponse(
        session_id=session_id,
        video_recording_url=f"/recordings/{session_id}/recording.webm",
        size_bytes=len(content),
    )


def _save_to_azure(session_id: str, content: bytes) -> RecordingUploadResponse:
    from azure.storage.blob import BlobServiceClient, ContentSettings

    settings = get_settings()
    blob_service = BlobServiceClient.from_connection_string(settings.azure_storage_connection_string)
    container = blob_service.get_container_client(settings.azure_storage_recordings_container)
    try:
        container.create_container()
    except Exception as exc:
        if getattr(exc, "status_code", None) != 409:
            raise

    blob_client = container.get_blob_client(f"{session_id}/recording.webm")
    blob_client.upload_blob(
        content,
        overwrite=True,
        content_settings=ContentSettings(content_type="video/webm"),
    )
    return RecordingUploadResponse(
        session_id=session_id,
        video_recording_url=blob_client.url,
        size_bytes=len(content),
        storage="blob",
    )
