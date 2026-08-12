"""핑퐁 루프 오케스트레이션 (§3 ①~⑥).

응답자 발화 1건이 들어오면:
  ③ 지시 큐에서 1건 pop (없으면 스킵)          <- D2 큐 소진형
  ④ 프롬프트 조립 (지시 은밀 주입)
  ⑤ GPT-4o가 다음 질문 + 판단 근거 생성
  ⑥ 인터뷰이에게 질문 전송 / 참관자에게 근거 포함 전송
"""

from __future__ import annotations

import logging

from app.schemas.messages import server_message
from app.schemas.session import Instruction, Session, Turn, utcnow
from app.services.ai import timekeeper
from app.services.ai.llm import get_question_generator
from app.services.connections import manager
from app.services.store import ack_instruction, get_store

logger = logging.getLogger(__name__)


def _turn_payload(turn: Turn, *, for_observer: bool) -> dict:
    """C5: 판단 근거(rationale)는 참관자 페이로드에만 포함한다."""
    data = turn.model_dump(mode="json")
    if not for_observer:
        data.pop("rationale", None)
    return data


async def handle_utterance(session: Session, text: str) -> None:
    store = get_store()

    # ① 응답자 발화 기록
    index = await store.next_turn_index(session.id)
    user_turn = Turn(index=index, speaker="interviewee", text=text)
    await store.append_turn(session.id, user_turn)
    await manager.broadcast_to_observers(
        session.id,
        server_message("transcript.append", turn=_turn_payload(user_turn, for_observer=True)),
    )

    # ③ 지시 큐에서 1건 pop. LPOP 자체가 ack이므로 재주입되지 않는다 (C4).
    instruction: Instruction | None = await store.pop_instruction(session.id)

    # ④⑤ 프롬프트 조립 + 다음 질문 생성
    transcript = await store.get_transcript(session.id)
    generator = get_question_generator()
    generated = await generator.generate(
        session=session,
        transcript=transcript,
        instruction=instruction,
        timekeeper_hint=timekeeper.latest_hint(session.id),
    )

    assistant_turn = Turn(
        index=index + 1,
        speaker="assistant",
        text=generated.text,
        rationale=generated.rationale,
        instruction_id=instruction.id if instruction else None,
    )
    await store.append_turn(session.id, assistant_turn)

    # 질문 트리 진행 위치 갱신
    if 0 <= generated.next_question_index <= len(session.questions):
        session.current_question_index = generated.next_question_index
    await store.save_session(session)

    # ⑥ 인터뷰이에게는 질문만 (근거 미포함)
    await manager.send_to_interviewee(
        session.id,
        server_message("assistant.question", turn=_turn_payload(assistant_turn, for_observer=False)),
    )
    # 참관자에게는 근거 포함
    await manager.broadcast_to_observers(
        session.id,
        server_message("transcript.append", turn=_turn_payload(assistant_turn, for_observer=True)),
    )

    if instruction is not None:
        applied = await ack_instruction(store, instruction, assistant_turn.index)
        await manager.broadcast_to_observers(
            session.id,
            server_message("instruction.applied", instruction=applied.model_dump(mode="json")),
        )


async def start_session_if_needed(session: Session) -> Session:
    if session.status == "created":
        session.status = "running"
        session.started_at = utcnow()
        await get_store().save_session(session)
    timekeeper.start(session.id)  # D5: 비동기 격리된 폴링 태스크 (C9)
    return session


async def end_session(session: Session) -> Session:
    session.status = "ended"
    session.ended_at = utcnow()
    await get_store().save_session(session)
    timekeeper.stop(session.id)
    # TODO(후순위, D6): Event Grid 이벤트 발행 -> Azure Functions 리포트 생성
    await manager.broadcast_to_observers(
        session.id, server_message("session.ended", session=session.model_dump(mode="json"))
    )
    return session
