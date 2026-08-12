"""타임키퍼 (D5, §4.3). MVP 필수.

메인 핑퐁 루프와 완전히 분리된 asyncio 태스크로 1분마다 폴링한다 (C9).
남은 시간 / 질문 커버리지를 보고 주제 전환이 필요하면 신호를 만들고,
그 신호는 (a) 참관자 대시보드로 브로드캐스트되고 (b) 다음 프롬프트 조립에 힌트로 들어간다.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from app.core.config import get_settings
from app.schemas.messages import server_message
from app.schemas.session import Session, utcnow
from app.services.connections import manager
from app.services.store import get_store

logger = logging.getLogger(__name__)


@dataclass
class TimekeeperSignal:
    should_move_on: bool
    remaining_minutes: float
    remaining_questions: int
    hint: str


def evaluate(session: Session) -> TimekeeperSignal:
    """룰 기반 1차 판단. Azure OpenAI mini 배포가 붙으면 이 함수를 프롬프트 호출로 대체."""
    started = session.started_at or session.created_at
    elapsed_minutes = (utcnow() - started).total_seconds() / 60
    remaining_minutes = max(session.duration_minutes - elapsed_minutes, 0.0)
    remaining_questions = max(len(session.questions) - session.covered_count(), 0)

    if remaining_questions == 0:
        return TimekeeperSignal(False, remaining_minutes, 0, "질문 리스트를 모두 다뤘습니다. 마무리 단계로 가세요.")

    # 남은 질문 1개당 필요한 최소 시간을 2분으로 잡고 여유가 없으면 전환 신호
    needed = remaining_questions * 2
    should_move_on = remaining_minutes < needed
    hint = (
        f"남은 시간 {remaining_minutes:.0f}분, 남은 질문 {remaining_questions}개. "
        + ("현재 주제를 정리하고 다음 질문으로 넘어가세요." if should_move_on else "현재 주제를 더 깊게 파도 됩니다.")
    )
    return TimekeeperSignal(should_move_on, remaining_minutes, remaining_questions, hint)


# 세션별 최신 힌트. 프롬프트 조립 시 참조한다.
_latest_hints: dict[str, str] = {}
_tasks: dict[str, asyncio.Task[None]] = {}


def latest_hint(session_id: str) -> str | None:
    return _latest_hints.get(session_id)


async def _loop(session_id: str) -> None:
    settings = get_settings()
    store = get_store()
    try:
        while True:
            await asyncio.sleep(settings.timekeeper_interval_seconds)
            session = await store.get_session(session_id)
            if session is None or session.status == "ended":
                break

            signal = evaluate(session)
            _latest_hints[session_id] = signal.hint
            await manager.broadcast_to_observers(
                session_id,
                server_message(
                    "timekeeper.signal",
                    should_move_on=signal.should_move_on,
                    remaining_minutes=round(signal.remaining_minutes, 1),
                    remaining_questions=signal.remaining_questions,
                    hint=signal.hint,
                ),
            )
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("타임키퍼 루프 오류 session=%s", session_id)
    finally:
        _tasks.pop(session_id, None)


def start(session_id: str) -> None:
    if session_id in _tasks:
        return
    _tasks[session_id] = asyncio.create_task(_loop(session_id))


def stop(session_id: str) -> None:
    task = _tasks.pop(session_id, None)
    if task is not None:
        task.cancel()
    _latest_hints.pop(session_id, None)
