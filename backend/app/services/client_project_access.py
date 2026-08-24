from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from fastapi import HTTPException, status

from app.core.config import get_settings


def _signing_secret() -> bytes:
    settings = get_settings()
    if settings.client_access_token_secret:
        return settings.client_access_token_secret.encode("utf-8")

    if settings.environment in {"local", "test"}:
        # Local 테스트 편의를 위한 개발 전용 키다. 운영 배포에는 환경 변수가 필수다.
        return b"local-development-client-access-secret"

    raise HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "Client project access is not configured.",
    )


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def issue_client_project_token(study_id: str) -> str:
    expires_at = int(time.time()) + get_settings().client_access_token_ttl_seconds
    payload = _encode(
        json.dumps(
            {"study_id": study_id, "expires_at": expires_at},
            separators=(",", ":"),
        ).encode("utf-8")
    )
    signature = _encode(
        hmac.new(
            _signing_secret(), payload.encode("ascii"), hashlib.sha256
        ).digest()
    )
    return f"{payload}.{signature}"


def verify_client_project_token(token: str | None, study_id: str) -> None:
    if not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "프로젝트 접근 권한이 없습니다.",
        )

    try:
        payload, signature = token.split(".", 1)
        expected = _encode(
            hmac.new(
                _signing_secret(), payload.encode("ascii"), hashlib.sha256
            ).digest()
        )
        data = json.loads(_decode(payload))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "프로젝트 접근 권한이 없습니다.",
        ) from None

    if not hmac.compare_digest(signature, expected) or data.get("study_id") != study_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "이 프로젝트에 접근할 수 없습니다.",
        )

    if not isinstance(data.get("expires_at"), int) or data["expires_at"] < int(time.time()):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "프로젝트 접근 권한이 만료되었습니다.",
        )
