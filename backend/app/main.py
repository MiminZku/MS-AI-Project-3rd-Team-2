"""FastAPI 엔트리포인트. Azure Container Apps에서 WebSocket 서버로 동작한다."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, sessions, rtc, avatar
from app.api.ws import interview, observer
from app.core.config import get_settings
from app.schemas.session import Session, QuestionNode
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
    # 로컬 개발 및 기본 접속 편의를 위한 기본 세션 자동 등록
    store = get_store()
    default_session = Session(
        id="default-session",
        title="배달앱 UX 및 배달비 만족도 조사",
        duration_minutes=25,
        questions=[
            QuestionNode(id="q1", order=1, text="최근 1주일간 배달앱을 몇 번 정도 이용하셨나요?"),
            QuestionNode(id="q2", order=2, text="배달앱을 고를 때 가장 중요하게 보는 기준은 무엇인가요?"),
            QuestionNode(id="q3", order=3, text="배달 팁이나 최소주문금액과 관련해서 가장 아쉬웠던 점이 있다면 말씀해 주세요."),
        ],
    )
    await store.save_session(default_session)
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
)

app.include_router(health.router)
app.include_router(sessions.router, prefix="/api")
app.include_router(rtc.router, prefix="/api")
app.include_router(avatar.router, prefix="/api")
app.include_router(interview.router)
app.include_router(observer.router)
