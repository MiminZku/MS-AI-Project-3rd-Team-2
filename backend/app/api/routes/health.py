"""헬스체크. Container Apps ingress 프로브와 CI 스모크 테스트가 사용한다."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, object]:
    settings = get_settings()
    return {
        "status": "ok",
        "environment": settings.environment,
        "store": "redis" if settings.use_redis else "memory",
        "llm": "azure-openai" if settings.use_azure_openai else "stub",
    }
