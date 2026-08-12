"""참관자 채널. 지시 입력 -> Redis 큐 적재 (§4.1-1,2)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.schemas.messages import server_message
from app.schemas.session import Instruction
from app.services.connections import manager
from app.services.store import get_store

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/observer/{session_id}")
async def observer_ws(websocket: WebSocket, session_id: str, token: str | None = None) -> None:
    expected = get_settings().admin_token
    if expected and token != expected:
        await websocket.close(code=4401, reason="관리자 토큰이 유효하지 않습니다.")
        return

    store = get_store()
    session = await store.get_session(session_id)
    if session is None:
        await websocket.close(code=4404, reason="세션을 찾을 수 없습니다.")
        return

    await manager.connect_observer(session_id, websocket)

    transcript = await store.get_transcript(session_id)
    instructions = await store.list_instructions(session_id)
    await websocket.send_json(
        server_message(
            "session.snapshot",
            session=session.model_dump(mode="json"),
            transcript=[turn.model_dump(mode="json") for turn in transcript],
            instructions=[ins.model_dump(mode="json") for ins in instructions],
            interviewee_connected=manager.has_interviewee(session_id),
        )
    )

    try:
        while True:
            message = await websocket.receive_json()
            msg_type = message.get("type")

            if msg_type == "instruction.create":
                text = (message.get("text") or "").strip()
                if not text:
                    continue
                # D3: 지시에 대한 AI 검토/재작성 없이 그대로 큐에 넣는다.
                instruction = Instruction(session_id=session_id, text=text)
                await store.push_instruction(instruction)
                await manager.broadcast_to_observers(
                    session_id,
                    server_message(
                        "instruction.queued", instruction=instruction.model_dump(mode="json")
                    ),
                )
            else:
                await websocket.send_json(
                    server_message("error", message=f"알 수 없는 메시지 타입: {msg_type}")
                )
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("참관자 소켓 오류 session=%s", session_id)
    finally:
        manager.disconnect_observer(session_id, websocket)
