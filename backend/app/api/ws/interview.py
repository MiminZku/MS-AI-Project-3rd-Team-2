"""인터뷰이 채널. 응답자는 참관자의 존재를 알 수 없어야 한다 (C5)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException

from app.schemas.messages import server_message
from app.services import orchestrator
from app.services.connections import manager
from app.services.store import get_store
from app.services.ai.realtime_stt import RealtimeSTTClient
from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Legacy POST API removed for Realtime STT


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

    settings = get_settings()
    stt_client = None
    translate_client = None

    utterance_buffer = []

    async def on_stt_partial(text: str):
        await manager.broadcast_to_observers(session_id, server_message("transcript.partial", lang="ko", text=text))
        
    async def on_stt_final(text: str):
        await manager.broadcast_to_observers(session_id, server_message("transcript.final", lang="ko", text=text))
        if text.strip():
            utterance_buffer.append(text.strip())

    async def on_translate_partial(text: str):
        await manager.broadcast_to_observers(session_id, server_message("transcript.partial", lang="en", text=text))
        
    async def on_translate_final(text: str):
        await manager.broadcast_to_observers(session_id, server_message("transcript.final", lang="en", text=text))

    try:
        while True:
            message = await websocket.receive_json()
            msg_type = message.get("type")

            if msg_type == "audio.start":
                source_lang = message.get("source_lang", "Korean")
                target_lang = message.get("target_lang", "English")
                # Initialize Realtime clients if not created
                if not stt_client and settings.use_azure_openai:
                    stt_client = RealtimeSTTClient(
                        session_id,
                        settings.azure_openai_realtime_stt_deployment,
                        on_stt_partial,
                        on_stt_final,
                        source_lang=source_lang,
                        target_lang=target_lang
                    )
                    await stt_client.connect()
                if not translate_client and settings.use_azure_openai:
                    translate_client = RealtimeSTTClient(
                        session_id,
                        settings.azure_openai_realtime_translate_deployment,
                        on_translate_partial,
                        on_translate_final,
                        source_lang=source_lang,
                        target_lang=target_lang
                    )
                    await translate_client.connect()
                    
            elif msg_type == "audio.chunk":
                b64_data = message.get("data")
                if b64_data:
                    if stt_client: await stt_client.send_audio_chunk(b64_data)
                    if translate_client: await translate_client.send_audio_chunk(b64_data)
                    
            elif msg_type == "audio.end":
                if stt_client: await stt_client.commit_audio()
                if translate_client: await translate_client.commit_audio()
                
                # VAD가 여러 번 발동했을 수 있으므로 모든 텍스트가 도착할 때까지 잠시 대기 후 하나로 합쳐서 질문 생성
                import asyncio
                await asyncio.sleep(1.5)
                
                full_text = " ".join(utterance_buffer).strip()
                utterance_buffer.clear()
                current = await store.get_session(session_id)
                if current and full_text:
                    await orchestrator.handle_utterance(current, full_text)
                
            elif msg_type == "utterance":
                # Fallback for text mode demo
                text = (message.get("text") or "").strip()
                if not text:
                    continue
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
        if stt_client:
            await stt_client.close()
        if translate_client:
            await translate_client.close()
            
        manager.disconnect_interviewee(session_id, websocket)
        await manager.broadcast_to_observers(
            session_id, server_message("interviewee.disconnected", session_id=session_id)
        )
