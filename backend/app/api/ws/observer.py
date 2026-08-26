"""참관자 채널. 지시 입력 -> Redis 큐 적재 (§4.1-1,2)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.schemas.messages import server_message
from app.schemas.session import Instruction
from app.services.ai.instruction_safety import review_instruction
from app.services.client_project_access import verify_client_project_token
from app.services.connections import manager
from app.services.store import get_store

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/observer/{session_id}")
async def observer_ws(
    websocket: WebSocket,
    session_id: str,
    token: str | None = None,
    client_token: str | None = None,
) -> None:
    store = get_store()
    session = await store.get_session(session_id)

    # 클라이언트는 프로젝트 접근 토큰으로 붙는다. 참관은 되지만 지시는 보낼 수 없다.
    # 지시는 세션을 만든 PM만 보낼 수 있어야 한다.
    viewer_role = "pm"
    if client_token:
        if session is None:
            await websocket.close(code=4404, reason="세션을 찾을 수 없습니다.")
            return
        if not session.study_id:
            await websocket.close(code=4403, reason="이 세션에 접근할 수 없습니다.")
            return
        try:
            verify_client_project_token(client_token, session.study_id)
        except HTTPException:
            await websocket.close(code=4403, reason="이 프로젝트에 접근할 수 없습니다.")
            return
        viewer_role = "client"
    else:
        expected = get_settings().admin_token
        if expected and token != expected:
            await websocket.close(code=4401, reason="관리자 토큰이 유효하지 않습니다.")
            return

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
            viewer_role=viewer_role,
        )
    )

    try:
        while True:
            message = await websocket.receive_json()
            msg_type = message.get("type")

            if msg_type == "instruction.create":
                if viewer_role != "pm":
                    # UI에서 숨기는 것만으로는 부족하다. 서버에서도 막는다.
                    await websocket.send_json(
                        server_message(
                            "error",
                            message="실시간 지시는 세션을 생성한 PM만 보낼 수 있습니다.",
                        )
                    )
                    continue

                text = (message.get("text") or "").strip()
                if not text:
                    continue

                # 책임있는 AI(공정성): 차별적 지시는 큐에 넣지 않는다.
                # 지시는 그대로 응답자에게 던져질 질문이 되므로 전달 전에 거른다.
                review = await review_instruction(text)
                if not review.allowed:
                    logger.warning(
                        "차별 소지로 실시간 지시 차단 session=%s",
                        session_id,
                    )
                    await websocket.send_json(
                        server_message(
                            "instruction.rejected",
                            text=text,
                            reason=review.reason,
                        )
                    )
                    continue

                # D3: 지시 내용 자체는 AI가 재작성하지 않고 그대로 큐에 넣는다.
                instruction = Instruction(session_id=session_id, text=text)
                await store.push_instruction(instruction)
                await manager.broadcast_to_observers(
                    session_id,
                    server_message(
                        "instruction.queued", instruction=instruction.model_dump(mode="json")
                    ),
                )
            elif msg_type == "instruction.delete":
                if viewer_role != "pm":
                    await websocket.send_json(
                        server_message(
                            "error",
                            message="실시간 지시는 세션을 생성한 PM만 관리할 수 있습니다.",
                        )
                    )
                    continue

                instruction_id = (message.get("instruction_id") or "").strip()
                if not instruction_id:
                    continue

                deleted = await store.delete_instruction(session_id, instruction_id)

                if not deleted:
                    # 이미 AI에게 전달됐거나(applied) 방금 소비된 지시는 취소할 수 없다.
                    await websocket.send_json(
                        server_message(
                            "error",
                            message="이미 전달된 지시는 취소할 수 없습니다.",
                        )
                    )
                    continue

                await manager.broadcast_to_observers(
                    session_id,
                    server_message("instruction.deleted", instruction_id=instruction_id),
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
