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
