"""Persistence for browser-recorded interview media."""

from __future__ import annotations

import asyncio
from pathlib import Path

from pydantic import BaseModel

from app.core.config import get_settings


LOCAL_RECORDINGS_DIR = Path(__file__).resolve().parents[2] / "data" / "recordings"


class RecordingUploadResponse(BaseModel):
    session_id: str
    video_recording_url: str
    size_bytes: int
    status: str = "uploaded"


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


async def save_recording(session_id: str, content: bytes) -> RecordingUploadResponse:
    """Save an interview recording to Azure Blob Storage or the local fallback."""
    settings = get_settings()
    if settings.azure_storage_connection_string:
        return await asyncio.to_thread(_save_to_azure, session_id, content)
    return await asyncio.to_thread(_save_locally, session_id, content)


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
    )
