"""공용 의존성."""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from app.core.config import get_settings
from app.schemas.session import Session
from app.services.store import get_store


async def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    """참관자(관리자) 전용 API 보호. ADMIN_TOKEN이 비어 있으면 검사하지 않는다."""
    expected = get_settings().admin_token
    if not expected:
        return
    if x_admin_token != expected:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "관리자 토큰이 유효하지 않습니다.")


async def load_session(session_id: str) -> Session:
    session = await get_store().get_session(session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "세션을 찾을 수 없습니다.")
    return session
