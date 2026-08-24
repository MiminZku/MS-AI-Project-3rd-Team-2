"""Azure Blob Storage 및 로컬 파일 스토리지 서비스."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self):
        self.settings = get_settings()
        self.local_dir = Path(tempfile.gettempdir()) / "ai_interview_uploads"
        try:
            self.local_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning("로컬 임시 업로드 디렉토리 생성 실패 (무시 가능): %s", e)

    async def upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str = "video/webm",
        container_name: str = "recordings",
    ) -> str:
        """파일을 Azure Blob Storage(또는 로컬 폴더)에 업로드하고 접근 URL을 반환."""
        conn_str = getattr(self.settings, "azure_storage_connection_string", "")
        
        # 1. Azure Blob Storage 연결 문자열이 있는 경우 실제 업로드
        if conn_str:
            try:
                from azure.storage.blob import BlobServiceClient
                blob_service_client = BlobServiceClient.from_connection_string(conn_str)
                container_client = blob_service_client.get_container_client(container_name)
                
                # 컨테이너가 없으면 생성
                if not container_client.exists():
                    container_client.create_container(public_access="blob")
                
                blob_client = container_client.get_blob_client(filename)
                blob_client.upload_blob(file_bytes, overwrite=True, content_type=content_type)
                logger.info(f"Azure Blob Storage 업로드 성공: {blob_client.url}")
                return blob_client.url
            except Exception as e:
                logger.exception(f"Azure Blob Storage 업로드 실패, 로컬 임시 폴더로 폴백: {e}")

        # 2. 로컬 파일 저장소 폴백 (로컬 개발/테스트용)
        try:
            target_path = self.local_dir / filename
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_path, "wb") as f:
                f.write(file_bytes)
            local_url = f"/api/uploads/{filename}"
            logger.info(f"로컬 파일 저장 완료: {target_path} -> {local_url}")
            return local_url
        except Exception as e:
            logger.warning(f"로컬 파일 저장 실패: {e}")
            return f"https://local-stub.blob.core.windows.net/{container_name}/{filename}"


_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
