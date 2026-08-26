"""타임키퍼 (D5, §4.3). MVP 필수.

메인 핑퐁 루프와 완전히 분리된 asyncio 태스크로 1분마다 폴링한다 (C9).
남은 시간 / 질문 커버리지를 보고 주제 전환이 필요하면 신호를 만들고,
그 신호는 (a) 참관자 대시보드로 브로드캐스트되고 (b) 다음 프롬프트 조립에 힌트로 들어간다.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Literal

from app.core.config import get_settings
from app.schemas.messages import server_message
from app.schemas.session import Session, utcnow
from app.services.connections import manager
from app.services.store import get_store

logger = logging.getLogger(__name__)


# 예정 시간 대비 진행 속도 분류.
#   ahead     : 시간이 남는다 -> 파생질문으로 더 깊이 파도 된다 (조기 종료 금지)
#   on_track  : 정상 페이스
#   behind    : 뒤처졌다 -> 파생질문은 건너뛰고 핵심(메인) 질문 위주로
#   overtime  : 예정 시간을 넘겼다 -> 남은 핵심 질문만 최소한으로 하고 즉시 마무리
Pace = Literal["ahead", "on_track", "behind", "overtime"]

# 마무리 인사에 남겨둘 시간(분). 이만큼 남았으면 새 질문을 시작하지 않는다.
WRAPUP_RESERVE_MINUTES = 1.5


@dataclass
class TimekeeperSignal:
    should_move_on: bool
    remaining_minutes: float
    remaining_questions: int
    hint: str
    pace: Pace = "on_track"
    elapsed_minutes: float = 0.0
    # 파생질문(Branch)·심화질문을 해도 되는 상황인지. 시간이 빠듯하면 False.
    allow_probes: bool = True
    # 대본을 다 마쳤는데 시간이 남아 더 파고들어야 하는 상황인지.
    should_deepen: bool = False


def evaluate(session: Session) -> TimekeeperSignal:
    """룰 기반 진행 속도 판단.

    "남은 질문 1개당 2분"이라는 고정 상수는 질문 수가 많은 세션에서 시작하자마자
    조기 마무리 신호를 띄웠고, 반대로 예정 시간을 넘겨도 멈추라는 신호가 없었다.

    지금은 두 축으로 본다:
      1) 진도 (covered_count vs 선형 배분 기대치) -> 파생질문을 할 여유가 있는가
      2) 절대 시간 (예정 시간을 넘겼는가)        -> 지금 당장 끝내야 하는가
    """
    started = session.started_at or session.created_at
    elapsed_minutes = (utcnow() - started).total_seconds() / 60
    duration_minutes = max(session.duration_minutes, 1)
    remaining_minutes = max(duration_minutes - elapsed_minutes, 0.0)
    total_questions = len(session.questions)
    covered_count = session.covered_count()
    remaining_questions = max(total_questions - covered_count, 0)

    def signal(pace: Pace, hint: str, *, should_deepen: bool = False) -> TimekeeperSignal:
        return TimekeeperSignal(
            should_move_on=pace in ("behind", "overtime"),
            remaining_minutes=remaining_minutes,
            remaining_questions=remaining_questions,
            hint=hint,
            pace=pace,
            elapsed_minutes=elapsed_minutes,
            allow_probes=pace in ("ahead", "on_track"),
            should_deepen=should_deepen,
        )

    # -----------------------------------------------------
    # 예정 시간 초과 — 진도와 무관하게 최우선
    # -----------------------------------------------------
    if remaining_minutes <= 0:
        overtime = elapsed_minutes - duration_minutes
        if remaining_questions == 0:
            return signal(
                "overtime",
                f"예정 시간을 {overtime:.0f}분 넘겼고 대본도 모두 마쳤습니다. "
                "새 질문 없이 지금 즉시 마무리 인사를 하세요.",
            )
        return signal(
            "overtime",
            f"예정 시간을 {overtime:.0f}분 넘겼는데 핵심 질문이 {remaining_questions}개 남았습니다. "
            "파생질문은 전부 건너뛰고 남은 핵심 질문만 빠르게 물은 뒤 마무리하세요.",
        )

    # -----------------------------------------------------
    # 대본을 모두 마친 상태
    # -----------------------------------------------------
    if remaining_questions == 0:
        if remaining_minutes > WRAPUP_RESERVE_MINUTES:
            return signal(
                "ahead",
                f"대본은 모두 마쳤지만 예정 시간이 아직 {remaining_minutes:.0f}분 남았습니다. "
                "아직 묻지 않은 파생질문이나 심화질문으로 더 들어가세요. 지금 종료하면 안 됩니다.",
                should_deepen=True,
            )
        return signal(
            "on_track",
            f"대본을 모두 마쳤고 남은 시간은 {remaining_minutes:.0f}분입니다. 마무리 단계로 가세요.",
        )

    # -----------------------------------------------------
    # 대본 진행 중 — 선형 배분 기대치와 비교
    # -----------------------------------------------------
    progress_ratio = min(elapsed_minutes / duration_minutes, 1.0)
    expected_done = total_questions * progress_ratio
    pace_detail = (
        f"남은 시간 {remaining_minutes:.0f}분, 남은 핵심 질문 {remaining_questions}개 "
        f"(정상 페이스라면 지금쯤 {expected_done:.1f}개 완료, 실제 {covered_count}개 완료). "
    )

    # 남은 시간에 남은 핵심 질문을 다 담을 수 있는지 (마무리 시간 제외)
    usable_minutes = max(remaining_minutes - WRAPUP_RESERVE_MINUTES, 0.0)
    minutes_per_question = usable_minutes / remaining_questions

    if covered_count < expected_done - 1 or minutes_per_question < 1.0:
        return signal(
            "behind",
            pace_detail + "진도가 뒤처졌습니다. 파생질문은 건너뛰고 핵심 질문 위주로 진행하세요.",
        )

    if covered_count > expected_done + 1:
        return signal(
            "ahead",
            pace_detail + "진도가 앞서 있습니다. 서두르지 말고 파생질문으로 충분히 파도 됩니다.",
        )

    return signal("on_track", pace_detail + "페이스가 정상입니다. 지금 주제를 충분히 파도 됩니다.")


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
                    pace=signal.pace,
                    elapsed_minutes=round(signal.elapsed_minutes, 1),
                    allow_probes=signal.allow_probes,
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
