"""인터뷰이 채널. 응답자는 참관자의 존재를 알 수 없어야 한다 (C5)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException

from app.schemas.messages import server_message
from app.services import orchestrator
from app.services.connections import manager
from app.services.store import get_store
from app.services.ai.stt import get_transcriber

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/api/interview/{session_id}/audio")
async def handle_audio(session_id: str, audio: UploadFile = File(...)) -> dict:
    store = get_store()
    session = await store.get_session(session_id)
    if not session or session.status != "running":
        raise HTTPException(status_code=400, detail="유효하지 않은 세션이거나 진행 중이 아닙니다.")
        
    audio_bytes = await audio.read()
    transcriber = get_transcriber()
    
    try:
        text = await transcriber.transcribe(audio_bytes, mime_type=audio.content_type or "audio/webm")
    except Exception as e:
        logger.exception("STT 에러")
        raise HTTPException(status_code=500, detail="음성 인식에 실패했습니다.")
        
    if not text.strip():
        return {"status": "ignored", "reason": "empty transcript"}
        
    await orchestrator.handle_utterance(session, text)
    return {"status": "success", "text": text}


@router.websocket("/ws/interview/{session_id}")
async def interview_ws(websocket: WebSocket, session_id: str) -> None:
    store = get_store()
    session = await store.get_session(session_id)
    if session is None:
        await websocket.close(code=4404, reason="세션을 찾을 수 없습니다.")
        return
    if session.status == "ended":
        await websocket.close(code=4410, reason="이미 종료된 세션입니다.")
        return

    await manager.connect_interviewee(session_id, websocket)
    session = await orchestrator.start_session_if_needed(session)

    await websocket.send_json(
        server_message(
            "session.state",
            session={
                "id": session.id,
                "title": session.title,
                "status": session.status,
                "duration_minutes": session.duration_minutes,
                "questions": [q.model_dump(mode="json") for q in session.questions],
            },
        )
    )
    await manager.broadcast_to_observers(
        session_id, server_message("interviewee.connected", session_id=session_id)
    )

    try:
        while True:
            message = await websocket.receive_json()
            msg_type = message.get("type")

            if msg_type == "utterance":
                # TODO(MVP): 오디오 프레임 수신 + endpointing(C2) 후 STT 결과를 여기에 넣는다.
                text = (message.get("text") or "").strip()
                if not text:
                    continue
                # 세션은 매 턴 다시 읽는다 — 다른 인스턴스가 갱신했을 수 있으므로 (D4)
                current = await store.get_session(session_id)
                if current is None:
                    break
                await orchestrator.handle_utterance(current, text)
            else:
                await websocket.send_json(
                    server_message("error", message=f"알 수 없는 메시지 타입: {msg_type}")
                )
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("인터뷰 소켓 오류 session=%s", session_id)
    finally:
        manager.disconnect_interviewee(session_id, websocket)
        await manager.broadcast_to_observers(
            session_id, server_message("interviewee.disconnected", session_id=session_id)
        )
