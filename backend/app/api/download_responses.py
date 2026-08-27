"""다운로드 응답 헬퍼.

PM용(/api/sessions, /api/projects)과 클라이언트용(/api/client/projects) 라우터가
같은 파일을 내려주도록 응답 생성 로직을 한 곳에 모은다.
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import HTTPException, status
from fastapi.responses import Response

from app.schemas.project_report import ProjectAggregateReport
from app.schemas.session import Session, Turn
from app.schemas.study import ResearchStudy
from app.services.downloads import (
    build_powerbi_excel_document,
    build_project_report_document,
    build_project_report_json,
    build_transcript_document,
    safe_filename_part,
)
from app.services.recordings import RecordingNotFound, load_recording


def _attachment_headers(filename: str) -> dict[str, str]:
    # 한글 파일명이 깨지지 않도록 RFC 5987 형식을 함께 준다.
    ascii_fallback = filename.encode("ascii", "ignore").decode("ascii") or "download"
    return {
        "Content-Disposition": (
            f'attachment; filename="{ascii_fallback}"; '
            f"filename*=UTF-8''{quote(filename)}"
        )
    }


def file_response(content: bytes, filename: str, media_type: str) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers=_attachment_headers(filename),
    )


def transcript_download_response(
    session: Session,
    turns: list[Turn],
    *,
    project_title: str | None = None,
) -> Response:
    content, filename, media_type = build_transcript_document(
        session,
        turns,
        project_title=project_title,
    )
    return file_response(content, filename, media_type)


async def recording_download_response(session: Session) -> Response:
    try:
        content = await load_recording(session.id, session.video_recording_url)
    except RecordingNotFound as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error

    filename = f"interview_{safe_filename_part(session.title, fallback=session.id)}.webm"
    return file_response(content, filename, "video/webm")


def project_report_download_response(
    study: ResearchStudy,
    report: ProjectAggregateReport | None,
    *,
    format: str = "word",
) -> Response:
    if report is None or report.status != "COMPLETED":
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "아직 생성된 프로젝트 리포트가 없습니다. 먼저 리포트를 생성해 주세요.",
        )

    fmt = (format or "word").lower().strip()
    if fmt in ("powerbi", "excel", "xlsx", "bi"):
        content, filename, media_type = build_powerbi_excel_document(study, report)
    elif fmt == "json":
        content, filename, media_type = build_project_report_json(study, report)
    else:
        content, filename, media_type = build_project_report_document(study, report)

    return file_response(content, filename, media_type)
