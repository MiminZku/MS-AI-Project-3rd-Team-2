"""세션 상태 + 참관자 지시 + 리포트 + ResearchStudy 저장소.

Redis 구현을 기본으로 사용하고,
REDIS_URL이 없으면 InMemoryStore를 사용한다.

Redis key 구조 예시:

  study:{id}                    JSON  ResearchStudy
  study:{id}:sessions           SET   Session ID

  session:{id}                  JSON  Session
  session:{id}:transcript       LIST  Turn JSON
  session:{id}:queue            LIST  대기 중 Instruction ID
  session:{id}:instructions     HASH  instruction_id -> Instruction JSON
  session:{id}:instr_order      LIST  Instruction 등록 순서
  session:{id}:report           JSON  AI Report
"""

from __future__ import annotations

from typing import Protocol

from app.core.config import get_settings
from app.schemas.report import Report
from app.schemas.project_report import ProjectAggregateReport

from app.schemas.session import (
    Instruction,
    Session,
    Turn,
    utcnow,
)
from app.schemas.study import ResearchStudy


# =========================================================
# Store Protocol
# =========================================================

class Store(Protocol):

    # -----------------------------------------------------
    # Research Study
    # -----------------------------------------------------

    async def save_study(
        self,
        study: ResearchStudy,
    ) -> None:
        ...

    async def get_study(
        self,
        study_id: str,
    ) -> ResearchStudy | None:
        ...

    async def get_study_by_access_id(
        self,
        access_id: str,
    ) -> ResearchStudy | None:
        ...

    async def list_studies(
        self,
    ) -> list[ResearchStudy]:
        ...

    async def delete_study(
        self,
        study_id: str,
    ) -> None:
        ...

    # -----------------------------------------------------
    # Session
    # -----------------------------------------------------

    async def save_session(
        self,
        session: Session,
    ) -> None:
        ...

    async def get_session(
        self,
        session_id: str,
    ) -> Session | None:
        ...

    async def list_sessions(
        self,
        study_id: str | None = None,
    ) -> list[Session]:
        ...

    async def delete_session(
        self,
        session_id: str,
    ) -> None:
        ...

    # -----------------------------------------------------
    # Transcript
    # -----------------------------------------------------

    async def append_turn(
        self,
        session_id: str,
        turn: Turn,
    ) -> None:
        ...

    async def get_transcript(
        self,
        session_id: str,
    ) -> list[Turn]:
        ...

    async def replace_transcript(
        self,
        session_id: str,
        turns: list[Turn],
    ) -> None:
        """전사 전체를 갈아끼운다.

        평소 인터뷰 흐름은 append만 쓴다. 이 메서드는 이미 저장된 턴에
        나중에 값을 채워 넣어야 하는 유지보수 작업(예: 번역 백필) 전용이다.
        """
        ...

    async def next_turn_index(
        self,
        session_id: str,
    ) -> int:
        ...

    # -----------------------------------------------------
    # Observer Instruction
    # -----------------------------------------------------

    async def push_instruction(
        self,
        instruction: Instruction,
    ) -> None:
        ...

    async def pop_instruction(
        self,
        session_id: str,
    ) -> Instruction | None:
        ...

    async def list_instructions(
        self,
        session_id: str,
    ) -> list[Instruction]:
        ...

    async def mark_applied(
        self,
        instruction: Instruction,
    ) -> None:
        ...

    async def delete_instruction(
        self,
        session_id: str,
        instruction_id: str,
    ) -> bool:
        """대기 중(queued)인 지시를 큐와 이력에서 제거한다.

        이미 응답자에게 전달된(applied) 지시는 인터뷰 기록의 일부이므로 지우지 않는다.
        실제로 삭제했으면 True.
        """
        ...

    # -----------------------------------------------------
    # Report
    # -----------------------------------------------------

    async def save_report(
        self,
        report: Report,
    ) -> None:
        ...

    async def get_report(

        self,
        session_id: str,
    ) -> Report | None:
        ...




    # -----------------------------------------------------
    # Project aggregate report
    # -----------------------------------------------------

    async def save_project_report(
        self,
        report: ProjectAggregateReport,
    ) -> None:
        ...

    async def get_project_report(
        self,
        project_id: str,
    ) -> ProjectAggregateReport | None:
        ...

    # -----------------------------------------------------
    # Close

    # -----------------------------------------------------

    async def close(self) -> None:
        ...


# =========================================================
# InMemory Store
# =========================================================

class InMemoryStore:
    """
    로컬 개발/테스트용 저장소.

    프로세스가 종료되면 모든 데이터가 사라진다.
    """

    def __init__(self) -> None:

        # Research Study
        self._studies: dict[str, ResearchStudy] = {}

        # Session
        self._sessions: dict[str, Session] = {}

        # Transcript
        self._transcripts: dict[str, list[Turn]] = {}

        # Instruction queue
        self._queue: dict[str, list[str]] = {}

        # Instructions
        self._instructions: dict[
            str,
            dict[str, Instruction],
        ] = {}

        # Session-level reports (legacy; no longer generated at interview end).
        self._reports: dict[str, Report] = {}



        # PM-created project aggregate report snapshots.
        self._project_reports: dict[str, ProjectAggregateReport] = {}



    # -----------------------------------------------------
    # Research Study
    # -----------------------------------------------------

    async def save_study(
        self,
        study: ResearchStudy,
    ) -> None:

        self._studies[study.id] = study


    async def get_study(
        self,
        study_id: str,
    ) -> ResearchStudy | None:

        return self._studies.get(study_id)


    async def get_study_by_access_id(
        self,
        access_id: str,
    ) -> ResearchStudy | None:

        return next(
            (
                study
                for study in self._studies.values()
                if study.access_id == access_id
            ),
            None,
        )


    async def list_studies(
        self,
    ) -> list[ResearchStudy]:

        studies = list(self._studies.values())
        studies.sort(key=lambda s: s.created_at, reverse=True)
        return studies


    async def delete_study(
        self,
        study_id: str,
    ) -> None:

        self._studies.pop(study_id, None)


    # -----------------------------------------------------
    # Session
    # -----------------------------------------------------

    async def save_session(
        self,
        session: Session,
    ) -> None:

        self._sessions[session.id] = session


    async def get_session(
        self,
        session_id: str,
    ) -> Session | None:

        return self._sessions.get(session_id)


    async def list_sessions(
        self,
        study_id: str | None = None,
    ) -> list[Session]:

        if study_id:
            sessions = [
                session
                for session in self._sessions.values()
                if session.study_id == study_id
            ]
        else:
            sessions = list(self._sessions.values())

        sessions.sort(
            key=lambda session: session.created_at,
            reverse=True,
        )

        return sessions


    async def delete_session(
        self,
        session_id: str,
    ) -> None:

        self._sessions.pop(session_id, None)
        self._transcripts.pop(session_id, None)
        self._queue.pop(session_id, None)
        self._instructions.pop(session_id, None)
        self._reports.pop(session_id, None)


    # -----------------------------------------------------
    # Transcript
    # -----------------------------------------------------

    async def append_turn(
        self,
        session_id: str,
        turn: Turn,
    ) -> None:

        self._transcripts.setdefault(
            session_id,
            [],
        ).append(turn)


    async def get_transcript(
        self,
        session_id: str,
    ) -> list[Turn]:

        return list(
            self._transcripts.get(
                session_id,
                [],
            )
        )


    async def replace_transcript(
        self,
        session_id: str,
        turns: list[Turn],
    ) -> None:

        self._transcripts[session_id] = list(turns)


    async def next_turn_index(
        self,
        session_id: str,
    ) -> int:

        return len(
            self._transcripts.get(
                session_id,
                [],
            )
        )


    # -----------------------------------------------------
    # Observer Instruction
    # -----------------------------------------------------

    async def push_instruction(
        self,
        instruction: Instruction,
    ) -> None:

        session_id = instruction.session_id

        self._instructions.setdefault(
            session_id,
            {},
        )[instruction.id] = instruction

        self._queue.setdefault(
            session_id,
            [],
        ).append(
            instruction.id
        )


    async def pop_instruction(
        self,
        session_id: str,
    ) -> Instruction | None:

        queue = (
            self._queue.get(session_id)
            or []
        )

        if not queue:
            return None

        instruction_id = queue.pop(0)

        return (
            self._instructions
            .get(session_id, {})
            .get(instruction_id)
        )


    async def list_instructions(
        self,
        session_id: str,
    ) -> list[Instruction]:

        return list(
            self._instructions
            .get(session_id, {})
            .values()
        )


    async def mark_applied(
        self,
        instruction: Instruction,
    ) -> None:

        self._instructions.setdefault(
            instruction.session_id,
            {},
        )[instruction.id] = instruction


    async def delete_instruction(
        self,
        session_id: str,
        instruction_id: str,
    ) -> bool:

        instructions = self._instructions.get(
            session_id,
            {},
        )

        instruction = instructions.get(
            instruction_id
        )

        if instruction is None or instruction.status != "queued":
            return False

        instructions.pop(
            instruction_id,
            None,
        )

        queue = self._queue.get(session_id)
        if queue and instruction_id in queue:
            queue.remove(instruction_id)

        return True


    # -----------------------------------------------------
    # Report
    # -----------------------------------------------------

    async def save_report(
        self,
        report: Report,
    ) -> None:
        self._reports[report.session_id] = report



    async def get_report(
        self,
        session_id: str,
    ) -> Report | None:

        return self._reports.get(
            session_id
        )





    # -----------------------------------------------------
    # Project aggregate report
    # -----------------------------------------------------

    async def save_project_report(
        self,
        report: ProjectAggregateReport,
    ) -> None:
        self._project_reports[report.project_id] = report


    async def get_project_report(
        self,
        project_id: str,
    ) -> ProjectAggregateReport | None:
        return self._project_reports.get(project_id)


    # -----------------------------------------------------
    # Close

    # -----------------------------------------------------

    async def close(self) -> None:
        return None


# =========================================================
# Redis Store
# =========================================================

class RedisStore:

    def __init__(
        self,
        url: str,
        ttl_seconds: int,
    ) -> None:

        import redis.asyncio as redis

        self._redis = redis.from_url(
            url,
            decode_responses=True,
        )

        self._ttl = ttl_seconds


    # -----------------------------------------------------
        # Redis Key
    # -----------------------------------------------------

    def _key(
        self,

        session_id: str,
        suffix: str = "",
    ) -> str:

        return f"session:{session_id}{suffix}"




    def _study_key(
        self,
        study_id: str,
    ) -> str:


        return f"study:{study_id}"


    def _study_sessions_key(
        self,
        study_id: str,
    ) -> str:


        return f"study:{study_id}:sessions"


    def _study_access_key(
        self,
        access_id: str,
    ) -> str:

        return f"project-access:{access_id}"




    def _project_report_key(
        self,
        project_id: str,
    ) -> str:
        return f"study:{project_id}:aggregate-report"



    # -----------------------------------------------------
    # Research Study
    # -----------------------------------------------------

    async def save_study(
        self,
        study: ResearchStudy,
    ) -> None:

        key = self._study_key(
            study.id
        )

        pipe = self._redis.pipeline()
        pipe.set(
            key,
            study.model_dump_json(),
            ex=self._ttl,
        )
        if study.access_id:
            pipe.set(
                self._study_access_key(study.access_id),
                study.id,
                ex=self._ttl,
            )
        await pipe.execute()


    async def get_study(
        self,
        study_id: str,
    ) -> ResearchStudy | None:

        raw = await self._redis.get(
            self._study_key(
                study_id
            )
        )

        if not raw:
            return None

        return (
            ResearchStudy
            .model_validate_json(raw)
        )


    async def get_study_by_access_id(
        self,
        access_id: str,
    ) -> ResearchStudy | None:

        study_id = await self._redis.get(
            self._study_access_key(access_id)
        )
        if not study_id:
            return None
        return await self.get_study(study_id)


    async def list_studies(
        self,
    ) -> list[ResearchStudy]:

        keys = await self._redis.keys("study:*")
        # filter out study:*:sessions
        study_keys = [k for k in keys if not k.endswith(":sessions")]
        if not study_keys:
            return []
        raws = await self._redis.mget(study_keys)
        studies = [ResearchStudy.model_validate_json(r) for r in raws if r]
        studies.sort(key=lambda s: s.created_at, reverse=True)
        return studies


    async def delete_study(
        self,
        study_id: str,
    ) -> None:

        study = await self.get_study(study_id)

        keys = [
            self._study_key(study_id),
            self._study_sessions_key(study_id),
        ]
        if study and study.access_id:
            keys.append(
                self._study_access_key(study.access_id)
            )

        await self._redis.delete(*keys)


    # -----------------------------------------------------
    # Session
    # -----------------------------------------------------

    async def save_session(
        self,
        session: Session,
    ) -> None:

        key = self._key(
            session.id
        )

        pipe = self._redis.pipeline()

        pipe.set(
            key,
            session.model_dump_json(),
            ex=self._ttl,
        )

        if session.study_id:
            study_sessions_key = (
                self._study_sessions_key(
                    session.study_id
                )
            )

            pipe.sadd(
                study_sessions_key,
                session.id,
            )

            pipe.expire(
                study_sessions_key,
                self._ttl,
            )

        await pipe.execute()


    async def get_session(
        self,
        session_id: str,
    ) -> Session | None:

        raw = await self._redis.get(
            self._key(
                session_id
            )
        )

        if not raw:
            return None

        return (
            Session
            .model_validate_json(raw)
        )


    async def list_sessions(
        self,
        study_id: str | None = None,
    ) -> list[Session]:

        if study_id:
            session_ids = list(
                await self._redis.smembers(
                    self._study_sessions_key(
                        study_id
                    )
                )
            )
        else:
            keys = await self._redis.keys("session:*")
            session_ids = [
                k.replace("session:", "")
                for k in keys
                if not any(k.endswith(s) for s in (":transcript", ":queue", ":instructions", ":instr_order", ":report", ":sessions"))
            ]

        if not session_ids:
            return []

        raws = await self._redis.mget(
            [
                self._key(session_id)
                for session_id in session_ids
            ]
        )

        sessions = [
            Session.model_validate_json(raw)
            for raw in raws
            if raw
        ]

        if study_id:
            sessions = [
                session
                for session in sessions
                if session.study_id == study_id
            ]

        sessions.sort(
            key=lambda session: session.created_at,
            reverse=True,
        )

        return sessions


    async def delete_session(
        self,
        session_id: str,
    ) -> None:

        session = await self.get_session(session_id)

        keys = [
            self._key(session_id),
            self._key(session_id, ":transcript"),
            self._key(session_id, ":queue"),
            self._key(session_id, ":instructions"),
            self._key(session_id, ":instr_order"),
            self._key(session_id, ":report"),
        ]

        await self._redis.delete(*keys)

        if session and session.study_id:
            await self._redis.srem(
                self._study_sessions_key(session.study_id),
                session_id,
            )


    # -----------------------------------------------------
    # Transcript
    # -----------------------------------------------------

    async def append_turn(
        self,
        session_id: str,
        turn: Turn,
    ) -> None:

        key = self._key(
            session_id,
            ":transcript",
        )

        await self._redis.rpush(
            key,
            turn.model_dump_json(),
        )

        await self._redis.expire(
            key,
            self._ttl,
        )


    async def get_transcript(
        self,
        session_id: str,
    ) -> list[Turn]:

        raws = await self._redis.lrange(
            self._key(
                session_id,
                ":transcript",
            ),
            0,
            -1,
        )

        return [
            Turn.model_validate_json(raw)
            for raw in raws
        ]


    async def replace_transcript(
        self,
        session_id: str,
        turns: list[Turn],
    ) -> None:

        key = self._key(
            session_id,
            ":transcript",
        )

        pipe = self._redis.pipeline()
        pipe.delete(key)

        if turns:
            pipe.rpush(
                key,
                *[turn.model_dump_json() for turn in turns],
            )
            pipe.expire(key, self._ttl)

        await pipe.execute()


    async def next_turn_index(
        self,
        session_id: str,
    ) -> int:

        return int(
            await self._redis.llen(
                self._key(
                    session_id,
                    ":transcript",
                )
            )
        )


    # -----------------------------------------------------
    # Observer Instruction
    # -----------------------------------------------------

    async def push_instruction(
        self,
        instruction: Instruction,
    ) -> None:

        session_id = (
            instruction.session_id
        )

        pipe = (
            self._redis.pipeline()
        )

        pipe.hset(
            self._key(
                session_id,
                ":instructions",
            ),
            instruction.id,
            instruction.model_dump_json(),
        )

        pipe.rpush(
            self._key(
                session_id,
                ":instr_order",
            ),
            instruction.id,
        )

        pipe.rpush(
            self._key(
                session_id,
                ":queue",
            ),
            instruction.id,
        )

        for suffix in (
            ":instructions",
            ":instr_order",
            ":queue",
        ):
            pipe.expire(
                self._key(
                    session_id,
                    suffix,
                ),
                self._ttl,
            )

        await pipe.execute()


    async def pop_instruction(
        self,
        session_id: str,
    ) -> Instruction | None:

        instruction_id = (
            await self._redis.lpop(
                self._key(
                    session_id,
                    ":queue",
                )
            )
        )

        if not instruction_id:
            return None

        raw = await self._redis.hget(
            self._key(
                session_id,
                ":instructions",
            ),
            instruction_id,
        )

        if not raw:
            return None

        return (
            Instruction
            .model_validate_json(raw)
        )


    async def list_instructions(
        self,
        session_id: str,
    ) -> list[Instruction]:

        order = await self._redis.lrange(
            self._key(
                session_id,
                ":instr_order",
            ),
            0,
            -1,
        )

        if not order:
            return []

        raws = await self._redis.hmget(
            self._key(
                session_id,
                ":instructions",
            ),
            order,
        )

        return [
            Instruction.model_validate_json(raw)
            for raw in raws
            if raw
        ]


    async def mark_applied(
        self,
        instruction: Instruction,
    ) -> None:

        await self._redis.hset(
            self._key(
                instruction.session_id,
                ":instructions",
            ),
            instruction.id,
            instruction.model_dump_json(),
        )


    async def delete_instruction(
        self,
        session_id: str,
        instruction_id: str,
    ) -> bool:

        raw = await self._redis.hget(
            self._key(
                session_id,
                ":instructions",
            ),
            instruction_id,
        )

        if not raw:
            return False

        instruction = Instruction.model_validate_json(
            raw
        )

        if instruction.status != "queued":
            return False

        pipe = self._redis.pipeline()

        # 대기 큐에서 제거 (LREM: 값이 일치하는 원소 1개)
        pipe.lrem(
            self._key(
                session_id,
                ":queue",
            ),
            1,
            instruction_id,
        )

        pipe.lrem(
            self._key(
                session_id,
                ":instr_order",
            ),
            1,
            instruction_id,
        )

        pipe.hdel(
            self._key(
                session_id,
                ":instructions",
            ),
            instruction_id,
        )

        await pipe.execute()

        return True


    # -----------------------------------------------------
    # Report
    # -----------------------------------------------------

    async def save_report(
        self,
        report: Report,
    ) -> None:
        await self._redis.set(
            self._key(report.session_id, ":report"),
            report.model_dump_json(),
            ex=self._ttl,
        )


    async def get_report(
        self,
        session_id: str,
    ) -> Report | None:
        raw = await self._redis.get(self._key(session_id, ":report"))


        if not raw:
            return None

        return (
            Report
            .model_validate_json(raw)
        )


    # -----------------------------------------------------
    # Project aggregate report
    # -----------------------------------------------------

    async def save_project_report(
        self,
        report: ProjectAggregateReport,
    ) -> None:
        await self._redis.set(
            self._project_report_key(report.project_id),
            report.model_dump_json(),
            ex=self._ttl,
        )


    async def get_project_report(
        self,
        project_id: str,
    ) -> ProjectAggregateReport | None:
        raw = await self._redis.get(self._project_report_key(project_id))
        return ProjectAggregateReport.model_validate_json(raw) if raw else None


    # -----------------------------------------------------
    # Close

    # -----------------------------------------------------

    async def close(self) -> None:

        await self._redis.aclose()


# =========================================================
# Store Singleton
# =========================================================

_store: Store | None = None


def get_store() -> Store:

    global _store

    if _store is None:

        settings = get_settings()

        if settings.use_cosmos:
            from app.services.cosmos_store import CosmosStore
            _store = CosmosStore(
                endpoint=settings.azure_cosmos_endpoint,
                key=settings.azure_cosmos_key,
                database_name=settings.azure_cosmos_database,
            )

        elif settings.use_redis:

            _store = RedisStore(
                settings.redis_url,
                settings.session_ttl_seconds,
            )

        else:

            _store = InMemoryStore()

    return _store


# =========================================================
# Store Close
# =========================================================

async def close_store() -> None:

    global _store

    if _store is not None:

        await _store.close()

        _store = None


# =========================================================
# Observer Instruction ACK
# =========================================================

async def ack_instruction(
    store: Store,
    instruction: Instruction,
    turn_index: int,
) -> Instruction:

    instruction.status = "applied"

    instruction.applied_at = utcnow()

    instruction.applied_turn = (
        turn_index
    )

    await store.mark_applied(
        instruction
    )

    return instruction
