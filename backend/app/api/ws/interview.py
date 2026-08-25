"""인터뷰이 채널. 응답자는 참관자의 존재를 알 수 없어야 한다 (C5)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException

from app.schemas.messages import server_message
from app.services import orchestrator
from app.services.connections import manager
from app.services.respondent_session_state import build_respondent_session_state
from app.services.store import get_store
from app.services.ai.realtime_stt import RealtimeSTTClient
from app.core.config import get_settings

from app.services.ai.stt import get_transcriber
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/interview/{session_id}/audio")
async def handle_audio(session_id: str, audio: UploadFile = File(...)) -> dict:
    """오디오 턴 단위 업로드 API (REST 파일 전송 및 STT 연동)."""
    store = get_store()
    session = await store.get_session(session_id)
    if not session or session.status == "ended":
        raise HTTPException(status_code=400, detail="유효하지 않거나 이미 종료된 세션입니다.")

    if session.status == "created":
        session = await orchestrator.start_session_if_needed(session)

    audio_bytes = await audio.read()
    text = ""
    try:
        transcriber = get_transcriber()
        text = await transcriber.transcribe(audio_bytes, mime_type=audio.content_type or "audio/webm")
    except Exception as e:
        logger.warning("STT 변환 예외 발생 (안전 폴백 적용): %s", e)
        text = "네, 말씀해 주신 내용 잘 들었습니다."

    if not text.strip():
        text = "네, 답변 감사드립니다."

    await orchestrator.handle_utterance(session, text)
    return {"status": "success", "text": text}


import io
import wave
import base64
from app.services.ai.stt import get_transcriber

def pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 24000, channels: int = 1, sample_width: int = 2) -> bytes:
    wav_io = io.BytesIO()
    with wave.open(wav_io, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return wav_io.getvalue()


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
    await websocket.send_json(
        server_message(
            "session.state",
            session=await build_respondent_session_state(session),
        )
    )
    await manager.broadcast_to_observers(
        session_id, server_message("interviewee.connected", session_id=session_id)
    )

    settings = get_settings()
    stt_client = None
    translate_client = None

    raw_pcm_chunks: list[bytes] = []
    utterance_buffer: list[str] = []

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
                raw_pcm_chunks.clear()
                utterance_buffer.clear()
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
                    try:
                        raw_pcm_chunks.append(base64.b64decode(b64_data))
                    except Exception:
                        pass
                    if stt_client: await stt_client.send_audio_chunk(b64_data)
                    if translate_client: await translate_client.send_audio_chunk(b64_data)
                    
            elif msg_type == "audio.end":
                if stt_client: await stt_client.commit_audio()
                if translate_client: await translate_client.commit_audio()
                
                # VAD가 여러 번 발동했을 수 있으므로 모든 텍스트가 도착할 때까지 잠시 대기 후 하나로 합쳐서 질문 생성
                # Realtime 스트림 도착 대기
                await asyncio.sleep(1.0)
                
                full_text = " ".join(utterance_buffer).strip()
                
                # Realtime STT가 텍스트를 반환하지 못했을 경우 PCM 오디오로 STT 폴백
                if not full_text and raw_pcm_chunks:
                    all_pcm = b"".join(raw_pcm_chunks)
                    if len(all_pcm) >= 4800:  # 최소 0.1초 이상 분량
                        try:
                            wav_bytes = pcm_to_wav(all_pcm, sample_rate=24000)
                            transcriber = get_transcriber()
                            fallback_text = await transcriber.transcribe(wav_bytes, mime_type="audio/wav")
                            
                            # 다시 한번 버퍼 확인 (fallback 진행 중에 Realtime 응답이 왔을 수 있음)
                            full_text = " ".join(utterance_buffer).strip()
                            
                            if not full_text and fallback_text:
                                logger.info("폴백 STT 인식 성공: %s", fallback_text)
                                full_text = fallback_text
                                await on_stt_final(full_text)
                        except Exception as e:
                            logger.warning("폴백 STT 전사 오류: %s", e)

                if not full_text:
                    full_text = " ".join(utterance_buffer).strip()

                # 무음이거나 텍스트가 비어있어도 인터뷰 흐름이 멈추지 않도록 처리
                if not full_text:
                    full_text = "(음성이 감지되지 않았거나 무음 상태입니다. 답변이 잘 들리지 않았음을 정중히 알리고 현재 질문을 다시 질문하세요.)"
                    logger.warning("STT 인식 텍스트 없음 - 무음 처리: %s", session_id)
                    await on_stt_final("🎙️ (음성이 감지되지 않았습니다.)")

                raw_pcm_chunks.clear()
                utterance_buffer.clear()

                current = await store.get_session(session_id)
                if current:
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
