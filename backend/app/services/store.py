"""세션 상태 + 참관자 지시 큐 저장소 (D4).

Redis 구현이 기본이고, REDIS_URL이 없으면 인메모리로 폴백한다.
폴백은 로컬 개발/CI 전용 — 인스턴스가 여러 개면 세션이 갈라지므로 배포에는 쓰지 말 것.

Redis 키 레이아웃
  session:{id}                 JSON  세션 본체
  session:{id}:transcript      LIST  Turn JSON (append only)
  session:{id}:queue           LIST  대기 중 지시 id (RPUSH -> LPOP = FIFO)
  session:{id}:instructions    HASH  instruction_id -> Instruction JSON (이력 = 대시보드 표시용)
  session:{id}:instr_order     LIST  instruction_id 등록 순서
"""

from __future__ import annotations

from typing import Protocol

from app.core.config import get_settings
from app.schemas.session import Instruction, Session, Turn, utcnow


class Store(Protocol):
    async def save_session(self, session: Session) -> None: ...
    async def get_session(self, session_id: str) -> Session | None: ...
    async def append_turn(self, session_id: str, turn: Turn) -> None: ...
    async def get_transcript(self, session_id: str) -> list[Turn]: ...
    async def next_turn_index(self, session_id: str) -> int: ...
    async def push_instruction(self, instruction: Instruction) -> None: ...
    async def pop_instruction(self, session_id: str) -> Instruction | None: ...
    async def list_instructions(self, session_id: str) -> list[Instruction]: ...
    async def mark_applied(self, instruction: Instruction) -> None: ...
    async def close(self) -> None: ...


class InMemoryStore:
    """단일 프로세스 폴백. 프로세스가 죽으면 전부 사라진다."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._transcripts: dict[str, list[Turn]] = {}
        self._queue: dict[str, list[str]] = {}
        self._instructions: dict[str, dict[str, Instruction]] = {}

    async def save_session(self, session: Session) -> None:
        self._sessions[session.id] = session

    async def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    async def append_turn(self, session_id: str, turn: Turn) -> None:
        self._transcripts.setdefault(session_id, []).append(turn)

    async def get_transcript(self, session_id: str) -> list[Turn]:
        return list(self._transcripts.get(session_id, []))

    async def next_turn_index(self, session_id: str) -> int:
        return len(self._transcripts.get(session_id, []))

    async def push_instruction(self, instruction: Instruction) -> None:
        sid = instruction.session_id
        self._instructions.setdefault(sid, {})[instruction.id] = instruction
        self._queue.setdefault(sid, []).append(instruction.id)

    async def pop_instruction(self, session_id: str) -> Instruction | None:
        queue = self._queue.get(session_id) or []
        if not queue:
            return None
        instruction_id = queue.pop(0)
        return self._instructions.get(session_id, {}).get(instruction_id)

    async def list_instructions(self, session_id: str) -> list[Instruction]:
        return list(self._instructions.get(session_id, {}).values())

    async def mark_applied(self, instruction: Instruction) -> None:
        self._instructions.setdefault(instruction.session_id, {})[instruction.id] = instruction

    async def close(self) -> None:
        return None


class RedisStore:
    def __init__(self, url: str, ttl_seconds: int) -> None:
        import redis.asyncio as redis  # 폴백 경로에서는 import하지 않도록 지연 로딩

        self._redis = redis.from_url(url, decode_responses=True)
        self._ttl = ttl_seconds

    def _key(self, session_id: str, suffix: str = "") -> str:
        return f"session:{session_id}{suffix}"

    async def save_session(self, session: Session) -> None:
        key = self._key(session.id)
        await self._redis.set(key, session.model_dump_json(), ex=self._ttl)

    async def get_session(self, session_id: str) -> Session | None:
        raw = await self._redis.get(self._key(session_id))
        return Session.model_validate_json(raw) if raw else None

    async def append_turn(self, session_id: str, turn: Turn) -> None:
        key = self._key(session_id, ":transcript")
        await self._redis.rpush(key, turn.model_dump_json())
        await self._redis.expire(key, self._ttl)

    async def get_transcript(self, session_id: str) -> list[Turn]:
        raws = await self._redis.lrange(self._key(session_id, ":transcript"), 0, -1)
        return [Turn.model_validate_json(raw) for raw in raws]

    async def next_turn_index(self, session_id: str) -> int:
        return int(await self._redis.llen(self._key(session_id, ":transcript")))

    async def push_instruction(self, instruction: Instruction) -> None:
        sid = instruction.session_id
        pipe = self._redis.pipeline()
        pipe.hset(self._key(sid, ":instructions"), instruction.id, instruction.model_dump_json())
        pipe.rpush(self._key(sid, ":instr_order"), instruction.id)
        pipe.rpush(self._key(sid, ":queue"), instruction.id)
        for suffix in (":instructions", ":instr_order", ":queue"):
            pipe.expire(self._key(sid, suffix), self._ttl)
        await pipe.execute()

    async def pop_instruction(self, session_id: str) -> Instruction | None:
        # LPOP 자체가 ack. 꺼낸 즉시 큐에서 사라지므로 다음 턴에 재주입되지 않는다 (C4).
        instruction_id = await self._redis.lpop(self._key(session_id, ":queue"))
        if not instruction_id:
            return None
        raw = await self._redis.hget(self._key(session_id, ":instructions"), instruction_id)
        return Instruction.model_validate_json(raw) if raw else None

    async def list_instructions(self, session_id: str) -> list[Instruction]:
        order = await self._redis.lrange(self._key(session_id, ":instr_order"), 0, -1)
        if not order:
            return []
        raws = await self._redis.hmget(self._key(session_id, ":instructions"), order)
        return [Instruction.model_validate_json(raw) for raw in raws if raw]

    async def mark_applied(self, instruction: Instruction) -> None:
        await self._redis.hset(
            self._key(instruction.session_id, ":instructions"),
            instruction.id,
            instruction.model_dump_json(),
        )

    async def close(self) -> None:
        await self._redis.aclose()


_store: Store | None = None


def get_store() -> Store:
    global _store
    if _store is None:
        settings = get_settings()
        _store = (
            RedisStore(settings.redis_url, settings.session_ttl_seconds)
            if settings.use_redis
            else InMemoryStore()
        )
    return _store


async def close_store() -> None:
    global _store
    if _store is not None:
        await _store.close()
        _store = None


async def ack_instruction(store: Store, instruction: Instruction, turn_index: int) -> Instruction:
    """pop한 지시를 applied로 확정 (§4.1-6, C4)."""
    instruction.status = "applied"
    instruction.applied_at = utcnow()
    instruction.applied_turn = turn_index
    await store.mark_applied(instruction)
    return instruction
