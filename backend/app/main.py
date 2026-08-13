"""FastAPI 엔트리포인트. Azure Container Apps에서 WebSocket 서버로 동작한다."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, sessions
from app.api.ws import interview, observer
from app.core.config import get_settings
from app.services.store import close_store, get_store

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper())
    logger.info(
        "기동: env=%s store=%s llm=%s",
        settings.environment,
        type(get_store()).__name__,
        "azure-openai" if settings.use_azure_openai else "stub",
    )
    yield
    await close_store()


settings = get_settings()

app = FastAPI(title="3자 개입형 실시간 AI 인터뷰 - 백엔드", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)ㄴㄴㅇㄴㅁㅇㅇㄴㄹ

app.include_router(health.router)
app.include_router(sessions.router, prefix="/api")
app.include_router(interview.router)
app.include_router(observer.router)
