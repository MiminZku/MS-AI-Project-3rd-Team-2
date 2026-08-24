"""FastAPI 엔트리포인트. Azure Container Apps에서 WebSocket 서버로 동작한다."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, sessions, studies, rtc, avatar, client_projects
from app.api.ws import interview, observer
from app.core.config import get_settings
from app.schemas.session import Session, QuestionNode
from app.schemas.study import ResearchStudy, InformationSlot
from app.services.project_access import issue_project_access_id
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
    store = get_store()

    # 1. 기본 데모 프로젝트(Studies) 시드 자동 등록
    try:
        existing_studies = await store.list_studies()
        if not existing_studies:
            demo_studies = [
                ResearchStudy(
                    id="proj_delivery_ux",
                    title="배달앱 UX 및 배달비 만족도 조사",
                    research_purpose="배달앱 사용자들의 UI 편의성 및 최근 배달비 인상에 대한 심리적 저항선을 파악합니다.",
                    question_script="1. 최근 배달앱 이용 빈도는 어느 정도인가요?\n2. 배달앱 선택 시 가장 중요하게 보는 요소는 무엇인가요?\n3. 배달비와 관련해 불만족스러웠던 경험이 있나요?",
                    questions=[
                        QuestionNode(id="q1", order=1, text="최근 1주일간 배달앱을 몇 번 정도 이용하셨나요?"),
                        QuestionNode(id="q2", order=2, text="배달앱을 고를 때 가장 중요하게 보는 기준은 무엇인가요?"),
                        QuestionNode(id="q3", order=3, text="배달 팁이나 최소주문금액과 관련해서 가장 아쉬웠던 점이 있다면 말씀해 주세요."),
                    ],
                    information_slots=[
                        InformationSlot(slot_id="s1", question_id="q1", slot_name="이용 빈도", description="주간 배달앱 주문 횟수", importance="high"),
                        InformationSlot(slot_id="s2", question_id="q2", slot_name="선택 기준", description="UI/UX, 혜택, 배달 속도 등", importance="high"),
                        InformationSlot(slot_id="s3", question_id="q3", slot_name="배달비 저항선", description="배달팁 체감 가격과 불만 요인", importance="high"),
                    ],
                ),
                ResearchStudy(
                    id="proj_ai_coding",
                    title="Claude Code vs OpenAI 터미널 개발 경험 심층 인터뷰",
                    research_purpose="개발자들의 터미널 AI 코딩 도구 사용 행태 및 모델 전환 요인을 분석합니다.",
                    question_script="1. 현재 주로 사용하는 AI 개발 도구 조합은 무엇인가요?\n2. 터미널 환경에서 Claude Code를 선택하게 되는 결정적 이유는 무엇인가요?\n3. OpenAI 모델 툴 사용 시 아쉬웠던 Pain Point는 무엇인가요?",
                    questions=[
                        QuestionNode(
                            id="q1",
                            order=1,
                            text="현재 터미널이나 개발 환경에서 주로 어떤 AI 툴 조합(Claude Code, Cursor 등)을 사용하고 계시나요?",
                            branches={"일상 코딩과 리팩토링 툴이 다를 때": "평소 일상적인 코딩과 복잡한 리팩토링 시 사용하는 툴이 다른가요?"},
                        ),
                        QuestionNode(
                            id="q2",
                            order=2,
                            text="개발자들 사이에서 '터미널 작업은 결국 Claude Code를 켜게 된다'는 이야기가 있는데, 이에 공감하시나요? 그 결정적인 이유는 무엇인가요?",
                            branches={
                                "UX/인터페이스 관점": "터미널 환경에서 대화의 흐름이나 멀티스텝 작업 처리가 어떻게 더 편리하다고 느끼시나요?",
                                "컨텍스트 관리 관점": "대규모 코드베이스를 읽고 수정할 때 의도를 더 잘 파악한다고 느끼는 순간이 있나요?",
                            },
                        ),
                        QuestionNode(
                            id="q3",
                            order=3,
                            text="반대로, OpenAI 관련 툴을 사용하면서 흐름이 끊기거나 답답했던 Pain Point가 있다면 말씀해 주세요.",
                            branches={
                                "수동 개입 번거로움": "프롬프트를 입력하고 결과물을 검토하는 과정에서 불필요하게 개입해야 했던 점이 있나요?",
                            },
                        ),
                    ],
                    information_slots=[
                        InformationSlot(slot_id="s1", question_id="q1", slot_name="주력 툴 체인", description="현재 개발 환경에서 사용하는 AI 툴", importance="high"),
                        InformationSlot(slot_id="s2", question_id="q2", slot_name="Claude Code 선호 이유", description="CLI UX 및 멀티턴 컨텍스트 유지력", importance="high"),
                        InformationSlot(slot_id="s3", question_id="q3", slot_name="OpenAI Pain Point", description="작업 중단 및 수동 수정 비효율", importance="high"),
                    ],
                ),
                ResearchStudy(
                    id="proj_subscription",
                    title="무료배달 멤버십 구독제 만족도 조사",
                    research_purpose="구독형 무료배달 서비스(와우, 요기패스, 배민클럽 등) 이용 만족도 및 이탈 의향을 파악합니다.",
                    question_script="1. 가입 중인 배달 멤버십 서비스가 있으신가요?\n2. 구독료 대비 혜택 체감도는 어느 정도인가요?\n3. 구독을 해지하거나 변경하고 싶었던 순간이 있었나요?",
                    questions=[
                        QuestionNode(id="q1", order=1, text="현재 이용 중이신 배달 무료 구독 멤버십(배민클럽, 와우 등)이 있으신가요?"),
                        QuestionNode(id="q2", order=2, text="매달 지불하는 구독료 대비 실제로 절약되는 금액이나 체감 만족도는 어떠신가요?"),
                        QuestionNode(id="q3", order=3, text="구독을 해지하고 싶거나 다른 서비스로 옮기고 싶었던 적이 있다면 어떤 이유였나요?"),
                    ],
                    information_slots=[
                        InformationSlot(slot_id="s1", question_id="q1", slot_name="구독 현황", description="이용 중인 멤버십 서비스 종류", importance="high"),
                        InformationSlot(slot_id="s2", question_id="q2", slot_name="체감 혜택", description="구독료 대비 절감액 및 만족도", importance="high"),
                        InformationSlot(slot_id="s3", question_id="q3", slot_name="이탈 트리거", description="해지 또는 서비스 전환 고려 요인", importance="high"),
                    ],
                ),
            ]
            for study in demo_studies:
                await store.save_study(study)
            logger.info("기본 데모 프로젝트 %d건 Cosmos DB 시드 등록 완료", len(demo_studies))

        # 기존 프로젝트도 Client 초대 흐름을 쓸 수 있도록 접속 ID를 보정한다.
        for study in await store.list_studies():
            if not study.access_id:
                study.access_id = await issue_project_access_id(store)
                await store.save_study(study)
    except Exception as e:
        logger.warning("데모 프로젝트 시드 등록 중 예외 (무시 가능): %s", e)

    # 2. 로컬 개발 및 기본 접속 편의를 위한 기본 세션 자동 등록
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
app.include_router(studies.router, prefix="/api")
app.include_router(studies.router, prefix="/api", tags=["studies"], include_in_schema=False) # alias
app.include_router(client_projects.router, prefix="/api")
app.include_router(rtc.router, prefix="/api")
app.include_router(avatar.router, prefix="/api")
app.include_router(interview.router)
app.include_router(observer.router)
