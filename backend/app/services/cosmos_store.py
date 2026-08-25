"""Azure Cosmos DB NoSQL 영구 저장소 구현체."""

from __future__ import annotations

import logging
from typing import Any
from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from app.core.config import get_settings
from app.schemas.report import Report
from app.schemas.session import Instruction, Session, Turn, utcnow
from app.schemas.study import ResearchStudy

logger = logging.getLogger(__name__)


class CosmosStore:
    def __init__(
        self,
        endpoint: str,
        key: str,
        database_name: str = "InterviewDB",
    ) -> None:
        self.endpoint = endpoint
        self.key = key
        self.database_name = database_name
        self.client: CosmosClient | None = None
        self.db = None
        self.projects_container = None
        self.interviews_container = None
        self._initialized = False

    async def _ensure_init(self) -> None:
        if self._initialized and self.client is not None:
            return

        try:
            self.client = CosmosClient(self.endpoint, credential=self.key)
            self.db = self.client.get_database_client(self.database_name)
            self.projects_container = self.db.get_container_client("projects")
            self.interviews_container = self.db.get_container_client("interviews")
            self._initialized = True
            logger.info("Cosmos DB 클라이언트 연결 초기화 완료 (%s)", self.database_name)
        except Exception as e:
            logger.exception("Cosmos DB 초기화 에러: %s", e)
            raise

    # -----------------------------------------------------
    # Research Study (Projects)
    # -----------------------------------------------------

    async def save_study(self, study: ResearchStudy) -> None:
        await self._ensure_init()
        doc = study.model_dump(mode="json")
        doc["type"] = "project"
        await self.projects_container.upsert_item(doc)
        logger.info("Cosmos DB: Project/Study 저장 완료 (id=%s)", study.id)

    async def get_study(self, study_id: str) -> ResearchStudy | None:
        await self._ensure_init()
        try:
            item = await self.projects_container.read_item(
                item=study_id,
                partition_key=study_id,
            )
            return ResearchStudy.model_validate(item)
        except CosmosResourceNotFoundError:
            return None
        except Exception as e:
            logger.warning("Cosmos DB Study 조회 실패: %s", e)
            return None

    async def get_study_by_access_id(
        self,
        access_id: str,
    ) -> ResearchStudy | None:
        await self._ensure_init()
        query = "SELECT * FROM c WHERE c.access_id = @access_id"
        parameters = [{"name": "@access_id", "value": access_id}]
        async for item in self.projects_container.query_items(
            query=query,
            parameters=parameters,
        ):
            return ResearchStudy.model_validate(item)
        return None

    async def list_studies(self) -> list[ResearchStudy]:
        await self._ensure_init()
        query = "SELECT * FROM c WHERE c.type = 'project' OR IS_DEFINED(c.question_script)"
        studies = []
        async for item in self.projects_container.query_items(
            query=query,
        ):
            try:
                studies.append(ResearchStudy.model_validate(item))
            except Exception as e:
                logger.warning("Study 문서 검증 실패 (id=%s): %s", item.get("id"), e)
        studies.sort(key=lambda s: s.created_at, reverse=True)
        return studies

    async def delete_study(self, study_id: str) -> None:
        await self._ensure_init()
        try:
            await self.projects_container.delete_item(
                item=study_id,
                partition_key=study_id,
            )
        except CosmosResourceNotFoundError:
            pass

    # -----------------------------------------------------
    # Session (Interviews)
    # -----------------------------------------------------

    async def save_session(self, session: Session) -> None:
        await self._ensure_init()
        # 기존 문서를 베이스로 병합한다 — 통째로 새로 쓰면 append_turn/push_instruction 등이
        # 같은 문서에 붙여둔 transcripts/instructions/report 필드가 지워진다.
        doc = await self._get_session_doc(session.id) or {}
        doc.update(session.model_dump(mode="json"))
        doc["type"] = "interview"
        doc["project_id"] = session.study_id or "default"
        await self.interviews_container.upsert_item(doc)
        logger.info("Cosmos DB: Interview/Session 저장 완료 (id=%s, project_id=%s)", session.id, doc["project_id"])

    async def get_session(self, session_id: str) -> Session | None:
        await self._ensure_init()
        # project_id를 모를 경우 쿼리로 검색
        query = "SELECT * FROM c WHERE c.id = @session_id"
        params = [{"name": "@session_id", "value": session_id}]
        async for item in self.interviews_container.query_items(
            query=query,
            parameters=params,
        ):
            return Session.model_validate(item)
        return None

    async def list_sessions(self, study_id: str | None = None) -> list[Session]:
        await self._ensure_init()
        if study_id:
            query = "SELECT * FROM c WHERE c.project_id = @study_id OR c.study_id = @study_id"
            params = [{"name": "@study_id", "value": study_id}]
            kwargs = {"parameters": params, "partition_key": study_id}
        else:
            query = "SELECT * FROM c WHERE c.type = 'interview' OR IS_DEFINED(c.duration_minutes)"
            kwargs = {}

        sessions = []
        async for item in self.interviews_container.query_items(
            query=query,
            **kwargs,
        ):
            try:
                sessions.append(Session.model_validate(item))
            except Exception as e:
                logger.warning("Session 문서 검증 실패 (id=%s): %s", item.get("id"), e)
        sessions.sort(key=lambda s: s.created_at, reverse=True)
        return sessions

    async def delete_session(self, session_id: str) -> None:
        await self._ensure_init()
        item = await self._get_session_doc(session_id)
        if not item:
            return
        try:
            await self.interviews_container.delete_item(
                item=session_id,
                partition_key=item.get("project_id", "default"),
            )
        except CosmosResourceNotFoundError:
            pass

    # -----------------------------------------------------
    # Transcript
    # -----------------------------------------------------

    async def append_turn(self, session_id: str, turn: Turn) -> None:
        await self._ensure_init()
        session = await self.get_session(session_id)
        if not session:
            return
        
        # Transcript는 세션 내부의 qa_records 또는 별도 sub-array로 함께 관리
        item = await self._get_session_doc(session_id)
        if not item:
            return

        if "transcripts" not in item:
            item["transcripts"] = []
        item["transcripts"].append(turn.model_dump(mode="json"))
        
        await self.interviews_container.upsert_item(item)

    async def get_transcript(self, session_id: str) -> list[Turn]:
        await self._ensure_init()
        item = await self._get_session_doc(session_id)
        if not item or "transcripts" not in item:
            return []
        return [Turn.model_validate(t) for t in item["transcripts"]]

    async def next_turn_index(self, session_id: str) -> int:
        transcripts = await self.get_transcript(session_id)
        return len(transcripts)

    async def _get_session_doc(self, session_id: str) -> dict[str, Any] | None:
        query = "SELECT * FROM c WHERE c.id = @session_id"
        params = [{"name": "@session_id", "value": session_id}]
        async for item in self.interviews_container.query_items(
            query=query,
            parameters=params,
        ):
            return item
        return None

    # -----------------------------------------------------
    # Observer Instruction
    # -----------------------------------------------------

    async def push_instruction(self, instruction: Instruction) -> None:
        await self._ensure_init()
        item = await self._get_session_doc(instruction.session_id)
        if not item:
            return
        if "instructions" not in item:
            item["instructions"] = {}
        if "instruction_queue" not in item:
            item["instruction_queue"] = []

        item["instructions"][instruction.id] = instruction.model_dump(mode="json")
        item["instruction_queue"].append(instruction.id)
        await self.interviews_container.upsert_item(item)

    async def pop_instruction(self, session_id: str) -> Instruction | None:
        await self._ensure_init()
        item = await self._get_session_doc(session_id)
        if not item or not item.get("instruction_queue"):
            return None
        
        ins_id = item["instruction_queue"].pop(0)
        ins_data = item.get("instructions", {}).get(ins_id)
        await self.interviews_container.upsert_item(item)
        if ins_data:
            return Instruction.model_validate(ins_data)
        return None

    async def list_instructions(self, session_id: str) -> list[Instruction]:
        await self._ensure_init()
        item = await self._get_session_doc(session_id)
        if not item or not item.get("instructions"):
            return []
        return [Instruction.model_validate(v) for v in item["instructions"].values()]

    async def mark_applied(self, instruction: Instruction) -> None:
        await self._ensure_init()
        item = await self._get_session_doc(instruction.session_id)
        if not item:
            return
        if "instructions" not in item:
            item["instructions"] = {}
        item["instructions"][instruction.id] = instruction.model_dump(mode="json")
        await self.interviews_container.upsert_item(item)

    # -----------------------------------------------------
    # Report
    # -----------------------------------------------------

    async def save_report(self, report: Report) -> None:
        await self._ensure_init()
        item = await self._get_session_doc(report.session_id)
        if item:
            item["report"] = report.model_dump(mode="json")
            await self.interviews_container.upsert_item(item)

    async def get_report(self, session_id: str) -> Report | None:
        await self._ensure_init()
        item = await self._get_session_doc(session_id)
        if item and "report" in item and item["report"]:
            return Report.model_validate(item["report"])
        return None

    async def close(self) -> None:
        if self.client:
            await self.client.close()
            self._initialized = False
