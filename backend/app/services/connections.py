"""세션별 WebSocket 연결 레지스트리.

세션 상태 자체는 Redis에 있고(D4) 여기에는 "지금 이 인스턴스에 붙어 있는 소켓"만 둔다.
인스턴스가 교체돼도 재접속하면 Redis에서 상태를 복구할 수 있는 구조.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class SessionConnections:
    interviewee: WebSocket | None = None
    observers: set[WebSocket] = field(default_factory=set)


class ConnectionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionConnections] = {}

    def _bucket(self, session_id: str) -> SessionConnections:
        return self._sessions.setdefault(session_id, SessionConnections())

    async def connect_interviewee(self, session_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._bucket(session_id).interviewee = ws

    async def connect_observer(self, session_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._bucket(session_id).observers.add(ws)

    def disconnect_interviewee(self, session_id: str, ws: WebSocket) -> None:
        bucket = self._sessions.get(session_id)
        if bucket and bucket.interviewee is ws:
            bucket.interviewee = None

    def disconnect_observer(self, session_id: str, ws: WebSocket) -> None:
        bucket = self._sessions.get(session_id)
        if bucket:
            bucket.observers.discard(ws)

    def has_interviewee(self, session_id: str) -> bool:
        bucket = self._sessions.get(session_id)
        return bool(bucket and bucket.interviewee is not None)

    async def send_to_interviewee(self, session_id: str, message: dict[str, Any]) -> None:
        bucket = self._sessions.get(session_id)
        if not bucket or bucket.interviewee is None:
            logger.warning(
                "인터뷰이 소켓 없음 (전송 생략) session=%s msg_type=%s",
                session_id,
                message.get("type"),
            )
            return
        try:
            await bucket.interviewee.send_json(message)
        except Exception as e:  # 소켓이 이미 끊긴 경우
            logger.warning("인터뷰이 전송 실패 session=%s error=%s", session_id, e)
            bucket.interviewee = None

    async def broadcast_to_observers(self, session_id: str, message: dict[str, Any]) -> None:
        bucket = self._sessions.get(session_id)
        if not bucket:
            return
        dead: list[WebSocket] = []
        for ws in list(bucket.observers):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            bucket.observers.discard(ws)


manager = ConnectionManager()
