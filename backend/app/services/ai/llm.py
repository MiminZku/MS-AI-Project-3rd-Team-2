"""다음 질문 생성 및 분기 판단 로직 (§4.2). Azure OpenAI GPT-4o 연동.

API 키가 없으면 스텁(Stub)으로 폴백한다. 스텁이어도 '참관자 지시 -> 다음 질문 반영' 흐름은
그대로 관찰되므로, Azure 리소스 없이 CI/CD와 파이프라인을 먼저 검증할 수 있다.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Protocol

from app.core.config import get_settings
from app.schemas.session import Instruction, Session, Turn
from app.services.ai.prompts import build_messages

logger = logging.getLogger(__name__)


@dataclass
class GeneratedQuestion:
    text: str
    rationale: str
    next_question_index: int
    is_sufficient: bool = True
    extracted_fact: str = ""
    selected_branch: str | None = None
    # STT 전사가 질문과 문맥상 맞지 않거나 알아들을 수 없을 때, 모델이 "이해한 척"하지 않고
    # 스스로 신고하는 플래그. True면 orchestrator가 다음 질문으로 넘어가지 않고 재확인시킨다.
    needs_clarification: bool = False
    # 이번 발화가 작별 인사(종료 멘트)라는 신고. True면 orchestrator가 이 발화를 전달한 뒤
    # 세션을 자동 종료한다 (대본을 모두 마쳤고 대기 중인 참관자 지시가 없을 때에 한함).
    is_closing: bool = False
    # 응답자의 직전 발화가 '현재 메인 질문에 대한 답변'이었는지에 대한 모델의 판단.
    # False면 질문을 물었을 뿐 답은 못 받은 것이므로 파생질문·전이로 넘어가지 않는다.
    is_answer_to_current_question: bool = True


class QuestionGenerator(Protocol):
    async def generate(
        self,
        session: Session,
        transcript: list[Turn],
        instruction: Instruction | None,
        timekeeper_hint: str | None = None,
    ) -> GeneratedQuestion: ...


class StubQuestionGenerator:
    """Azure 미연결 상태에서 파이프라인을 검증하기 위한 스텁 구현."""

    async def generate(
        self,
        session: Session,
        transcript: list[Turn],
        instruction: Instruction | None,
        timekeeper_hint: str | None = None,
    ) -> GeneratedQuestion:
        index = session.current_question_index
        questions = session.questions

        if instruction is not None:
            return GeneratedQuestion(
                text=f"방금 말씀 중에 궁금한 점이 있는데요, {instruction.text} 관련해서 조금 더 들려주시겠어요?",
                rationale=f"[STUB] 참관자 지시 '{instruction.text}'를 이번 턴에 주입했습니다.",
                next_question_index=index,
                is_sufficient=False,
                extracted_fact="참관자 지시 질문 수행",
                selected_branch=None,
            )

        # 아직 전달되지 않은 메인 질문이 있으면 파생질문보다 항상 먼저 묻는다.
        if index < len(questions) and not session.main_question_asked:
            return GeneratedQuestion(
                text=questions[index].text,
                rationale="[STUB] 아직 묻지 않은 메인 질문을 순서대로 진행했습니다.",
                next_question_index=index,
                is_sufficient=False,
                extracted_fact="",
                selected_branch=None,
            )

        # 메인 질문 답변을 받은 뒤에만 분기(Branch) 키워드를 확인한다
        last_turn = transcript[-1] if transcript else None
        if last_turn and last_turn.speaker == "interviewee" and index < len(questions):
            curr_q = questions[index]
            for branch_k, branch_q in curr_q.branches.items():
                if branch_k in last_turn.text and branch_k not in session.taken_branches:
                    return GeneratedQuestion(
                        text=branch_q,
                        rationale=f"[STUB] 응답자의 키워드 '{branch_k}'에 매칭되어 파생 꼬리질문으로 전이했습니다.",
                        next_question_index=index,
                        is_sufficient=False,
                        extracted_fact=f"{branch_k} 키워드 언급",
                        selected_branch=branch_k,
                    )

        # 현재 질문을 마무리하고 같은 발화에서 다음 메인 질문을 그대로 묻는다
        if index + 1 < len(questions):
            return GeneratedQuestion(
                text=questions[index + 1].text,
                rationale="[STUB] 현재 질문의 답변을 받아 다음 메인 질문으로 전이했습니다.",
                next_question_index=index + 1,
                is_sufficient=True,
                extracted_fact="",
                selected_branch=None,
            )

        if index < len(questions):
            return GeneratedQuestion(
                text="준비된 기본 질문은 모두 마쳤습니다! 혹시 참관 중인 리서치팀에서 추가로 확인하고 싶은 내용이 있는지 잠시 확인해 보겠습니다. 잠시만 기다려 주세요.",
                rationale="[WRAPUP] 마지막 질문의 답변까지 받아 리서치팀 추가 질문 확인 단계로 진입했습니다.",
                next_question_index=len(questions),
                is_sufficient=True,
                extracted_fact="",
                selected_branch=None,
            )

        # 대본 종료 구간(index == len(questions))에서는 인덱스가 더 올라가지 않으므로,
        # 마무리 멘트를 이미 했는지는 대화 기록으로 판별한다. (같은 멘트 무한 반복 방지)
        already_wrapped_up = any(
            turn.speaker == "assistant" and (turn.rationale or "").startswith("[WRAPUP]")
            for turn in transcript
        )
        if not already_wrapped_up:
            return GeneratedQuestion(
                text="준비된 기본 질문은 모두 마쳤습니다! 혹시 참관 중인 리서치팀에서 추가로 확인하고 싶은 내용이 있는지 잠시 확인해 보겠습니다. 잠시만 기다려 주세요.",
                rationale="[WRAPUP] 기본 질문 리스트를 모두 완료하여 리서치팀 추가 질문 확인 단계로 진입했습니다.",
                next_question_index=index,
                is_sufficient=True,
                extracted_fact="",
                selected_branch=None,
            )

        return GeneratedQuestion(
            text="확인 결과 추가 질문은 없으므로 오늘 인터뷰를 모두 마치겠습니다. 성실하고 소중한 답변 진심으로 감사드립니다! 상단의 나가기 버튼을 눌러 퇴장해 주시면 됩니다.",
            rationale="[END] 모든 인터뷰 절차가 성공적으로 종료되었습니다.",
            next_question_index=index,
            is_sufficient=True,
            extracted_fact="",
            selected_branch=None,
            is_closing=True,
        )


class AzureOpenAIQuestionGenerator:
    def __init__(self) -> None:
        from openai import AsyncAzureOpenAI  # 스텁 경로에서는 로드되지 않도록 지연 import

        settings = get_settings()
        self._deployment = settings.azure_openai_chat_deployment
        self._client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )

    async def generate(
        self,
        session: Session,
        transcript: list[Turn],
        instruction: Instruction | None,
        timekeeper_hint: str | None = None,
    ) -> GeneratedQuestion:
        messages = build_messages(session, transcript, instruction, timekeeper_hint)
        response = await self._client.chat.completions.create(
            model=self._deployment,
            messages=messages,
            temperature=0.3,
            max_completion_tokens=1000,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("GPT 응답 JSON 파싱 실패, 원문을 질문으로 사용: %s", content[:200])
            data = {"question": content.strip()}

        next_idx = int(data.get("next_question_index", session.current_question_index))
        is_sufficient = bool(data.get("is_sufficient", True))
        extracted_fact = str(data.get("extracted_fact", "")).strip()
        needs_clarification = bool(data.get("needs_clarification", False))
        is_closing = bool(data.get("is_closing", False))
        is_answer = bool(data.get("is_answer_to_current_question", True))
        selected_branch = data.get("selected_branch")
        if selected_branch:
            selected_branch = str(selected_branch).strip()
            if selected_branch.lower() in ("null", "none", ""):
                selected_branch = None

        # State Machine Guard: Prevent jumping backward or skipping multiple steps
        if next_idx < session.current_question_index:
            next_idx = session.current_question_index
        elif next_idx > session.current_question_index + 1:
            next_idx = session.current_question_index + 1

        total_questions = len(session.questions)
        if session.current_question_index >= total_questions:
            next_idx = total_questions

        return GeneratedQuestion(
            text=str(data.get("question", "")).strip() or "조금 더 자세히 말씀해 주시겠어요?",
            rationale=str(data.get("rationale", "")).strip(),
            next_question_index=next_idx,
            is_sufficient=is_sufficient,
            extracted_fact=extracted_fact,
            selected_branch=selected_branch,
            needs_clarification=needs_clarification,
            is_closing=is_closing,
            is_answer_to_current_question=is_answer,
        )


_generator: QuestionGenerator | None = None


def get_question_generator() -> QuestionGenerator:
    global _generator
    if _generator is None:
        if get_settings().use_azure_openai:
            _generator = AzureOpenAIQuestionGenerator()
        else:
            logger.warning("AZURE_OPENAI_* 미설정 — StubQuestionGenerator로 동작합니다.")
            _generator = StubQuestionGenerator()
    return _generator

