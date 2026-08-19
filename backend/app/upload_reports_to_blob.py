from __future__ import annotations

import json
import os
from pathlib import Path

from azure.storage.blob import (
    BlobServiceClient,
    ContentSettings,
)
from dotenv import load_dotenv


# =========================================================
# 경로
# =========================================================

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent

REPORT_DIR = (
    APP_DIR
    / "ai-interview-report"
)

STUDY_REPORT_JSON = (
    REPORT_DIR
    / "study_report.json"
)

WORD_REPORT = (
    REPORT_DIR
    / "study_report.docx"
)

POWERBI_REPORT = (
    REPORT_DIR
    / "study_report_powerbi.xlsx"
)


# =========================================================
# 환경변수
# =========================================================

load_dotenv(
    BACKEND_DIR / ".env"
)

CONNECTION_STRING = (
    os.getenv(
        "AZURE_STORAGE_CONNECTION_STRING",
        "",
    )
    .strip()
)

CONTAINER_NAME = "reports"


# =========================================================
# Study ID 읽기
# =========================================================

def get_study_id() -> str:

    if not STUDY_REPORT_JSON.exists():
        raise FileNotFoundError(
            f"Study Report가 없습니다: "
            f"{STUDY_REPORT_JSON}"
        )

    data = json.loads(
        STUDY_REPORT_JSON.read_text(
            encoding="utf-8"
        )
    )

    overview = (
        data.get("overview")
        or {}
    )

    study_id = (
        overview.get("study_id")
        or "unknown-study"
    )

    return str(
        study_id
    ).strip()


# =========================================================
# Content-Type
# =========================================================

def get_content_settings(
    file_path: Path,
) -> ContentSettings:

    suffix = (
        file_path.suffix
        .lower()
    )

    if suffix == ".json":
        return ContentSettings(
            content_type=(
                "application/json; charset=utf-8"
            )
        )

    if suffix == ".docx":
        return ContentSettings(
            content_type=(
                "application/"
                "vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            )
        )

    if suffix == ".xlsx":
        return ContentSettings(
            content_type=(
                "application/"
                "vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
        )

    return ContentSettings(
        content_type=(
            "application/octet-stream"
        )
    )


# =========================================================
# 파일 하나 업로드
# =========================================================

def upload_file(
    blob_service_client: BlobServiceClient,
    study_id: str,
    file_path: Path,
) -> str:

    if not file_path.exists():
        raise FileNotFoundError(
            f"업로드할 파일이 없습니다: "
            f"{file_path}"
        )

    blob_name = (
        f"{study_id}/"
        f"{file_path.name}"
    )

    blob_client = (
        blob_service_client
        .get_blob_client(
            container=CONTAINER_NAME,
            blob=blob_name,
        )
    )

    with file_path.open(
        "rb"
    ) as file_data:

        blob_client.upload_blob(
            data=file_data,
            overwrite=True,
            content_settings=(
                get_content_settings(
                    file_path
                )
            ),
        )

    return blob_name


# =========================================================
# 메인
# =========================================================

def main() -> None:

    if not CONNECTION_STRING:
        raise RuntimeError(
            "AZURE_STORAGE_CONNECTION_STRING이 "
            ".env에 없습니다."
        )

    study_id = (
        get_study_id()
    )

    print()
    print(
        "========================================"
    )
    print(
        "Azure Blob Report Upload"
    )
    print(
        "========================================"
    )

    print(
        f"Study ID: {study_id}"
    )

    print(
        f"Container: {CONTAINER_NAME}"
    )

    blob_service_client = (
        BlobServiceClient
        .from_connection_string(
            CONNECTION_STRING
        )
    )

    files = [
        STUDY_REPORT_JSON,
        WORD_REPORT,
        POWERBI_REPORT,
    ]

    uploaded_blob_names: list[
        str
    ] = []

    for file_path in files:

        blob_name = upload_file(
            blob_service_client=(
                blob_service_client
            ),
            study_id=study_id,
            file_path=file_path,
        )

        uploaded_blob_names.append(
            blob_name
        )

        print(
            f"✅ 업로드 완료: "
            f"{blob_name}"
        )

    # =====================================================
    # 실제 Blob에 존재하는지 다시 조회
    # =====================================================

    container_client = (
        blob_service_client
        .get_container_client(
            CONTAINER_NAME
        )
    )

    existing_blob_names = {
        blob.name
        for blob
        in container_client.list_blobs(
            name_starts_with=(
                f"{study_id}/"
            )
        )
    }

    print()
    print(
        "업로드 검증:"
    )

    for blob_name in (
        uploaded_blob_names
    ):

        if (
            blob_name
            in existing_blob_names
        ):
            print(
                f"✅ 확인됨: "
                f"{blob_name}"
            )

        else:
            print(
                f"❌ 찾을 수 없음: "
                f"{blob_name}"
            )

    print()
    print(
        "========================================"
    )
    print(
        "Blob Storage 업로드 완료 ✅"
    )
    print(
        "========================================"
    )


if __name__ == "__main__":
    main()