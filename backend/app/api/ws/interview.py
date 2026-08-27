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
from app.services.ai.translation import language_name, translate_text
from app.core.config import get_settings

from app.services.ai.stt import get_transcriber
from app.services.ai.stt_judge import get_transcript_validator
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/interview/{session_id}/audio")
async def handle_audio(session_id: str, audio: UploadFile = File(...)) -> dict:
    """오디오 턴 단위 업로드 API (REST 파일 전송 및 Dual-pass STT & Judge 연동)."""
    store = get_store()
    session = await store.get_session(session_id)
    if not session or session.status == "ended":
        raise HTTPException(status_code=400, detail="유효하지 않거나 이미 종료된 세션입니다.")

    if session.status == "created":
        session = await orchestrator.start_session_if_needed(session)

    audio_bytes = await audio.read()
    curr_q = ""
    if session.questions and 0 <= session.current_question_index < len(session.questions):
        curr_q = session.questions[session.current_question_index].text

    text = ""
    try:
        transcriber = get_transcriber()
        val_res = await transcriber.transcribe_dual_pass(
            audio_bytes, question_context=curr_q, mime_type=audio.content_type or "audio/webm"
        )
        text = val_res.selected
        if val_res.status == "low_confidence":
            logger.info("REST STT Judge Low Confidence 판정 (%s): %s", session_id, val_res.reason)
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
    translate_buffer: list[str] = []

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
        if text.strip():
            translate_buffer.append(text.strip())

    try:
        while True:
            message = await websocket.receive_json()
            msg_type = message.get("type")

            if msg_type == "audio.start":
                raw_pcm_chunks.clear()
                utterance_buffer.clear()
                translate_buffer.clear()
                if stt_client:
                    stt_client.reset_buffer()
                if translate_client:
                    translate_client.reset_buffer()
                source_lang = message.get("source_lang", "Korean")
                target_lang = message.get("target_lang", "English")

                # Realtime 세션은 턴이 끝나거나 유휴 상태가 되면 서버가 닫는다.
                # 예전에는 클라이언트 객체가 남아 있다는 이유로 재연결을 안 해서,
                # 한 번 끊기면 그 세션 내내 동시통역이 죽어 있었다 (첫 발화만 번역됨).
                # 매 발화 시작마다 살아 있는지 확인하고 필요하면 다시 붙인다.
                if settings.use_azure_openai:
                    if stt_client is None:
                        stt_client = RealtimeSTTClient(
                            session_id,
                            settings.azure_openai_realtime_stt_deployment,
                            on_stt_partial,
                            on_stt_final,
                            source_lang=source_lang,
                            target_lang=target_lang
                        )
                        await stt_client.connect()
                    else:
                        await stt_client.ensure_connected()

                    if translate_client is None:
                        translate_client = RealtimeSTTClient(
                            session_id,
                            settings.azure_openai_realtime_translate_deployment,
                            on_translate_partial,
                            on_translate_final,
                            source_lang=source_lang,
                            target_lang=target_lang
                        )
                        await translate_client.connect()
                    else:
                        await translate_client.ensure_connected()

                    if not translate_client.is_alive():
                        logger.warning(
                            "동시통역 Realtime 연결 실패 — 이번 발화는 텍스트 번역으로 대체합니다 session=%s",
                            session_id,
                        )
                    
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
                
                # Realtime 스트림 도착 대기
                await asyncio.sleep(0.8)
                
                realtime_candidate = " ".join(utterance_buffer).strip()
                realtime_translation = " ".join(translate_buffer).strip() or (translate_client.current_text.strip() if translate_client else "")
                
                current = await store.get_session(session_id)
                curr_q = ""
                if current and current.questions and 0 <= current.current_question_index < len(current.questions):
                    curr_q = current.questions[current.current_question_index].text

                final_text = ""
                validator = get_transcript_validator()
                
                if raw_pcm_chunks:
                    all_pcm = b"".join(raw_pcm_chunks)
                    if len(all_pcm) >= 4800:  # 최소 0.1초 이상 분량
                        try:
                            wav_bytes = pcm_to_wav(all_pcm, sample_rate=24000)
                            transcriber = get_transcriber()
                            
                            if realtime_candidate and transcriber.gpt_transcriber:
                                # 1차 Realtime STT 텍스트와 2차 Whisper STT 텍스트를 대조 검증
                                whisper_candidate = await transcriber.gpt_transcriber.transcribe(wav_bytes, mime_type="audio/wav")
                                val_result = await validator.validate(curr_q, realtime_candidate, whisper_candidate)
                                final_text = val_result.selected
                                if val_result.status == "low_confidence":
                                    logger.info("WebSocket STT Judge Low Confidence: %s", val_result.reason)
                            else:
                                # Realtime 수신이 없었을 경우 Dual-Pass 전사기 전체 가동
                                val_result = await transcriber.transcribe_dual_pass(wav_bytes, question_context=curr_q, mime_type="audio/wav")
                                final_text = val_result.selected
                        except Exception as e:
                            logger.warning("Dual-pass STT 검증 오류: %s", e)
                            final_text = realtime_candidate

                if not final_text:
                    final_text = realtime_candidate or " ".join(utterance_buffer).strip()

                if final_text:
                    await on_stt_final(final_text)
                else:
                    final_text = "(음성이 감지되지 않았거나 무음 상태입니다. 마지막 답변이 잘 들리지 않았음을 정중히 알리고 다시 말씀해주시겠어요? 라고 재질문하세요.)"
                    logger.warning("STT 인식 텍스트 없음 - 무음 처리: %s", session_id)
                    await on_stt_final("🎙️ (음성이 감지되지 않았습니다.)")

                # 실시간 통역이 이번 발화를 놓쳤으면(연결 끊김 등) 확정 텍스트를 번역해 채운다.
                # 백룸 영어 자막이 통째로 비는 것보다 조금 늦게라도 붙는 편이 낫다.
                if final_text and not realtime_translation:
                    fallback = await translate_text(
                        final_text,
                        target_language=language_name(
                            current.interpretation_language if current else None
                        ),
                    )
                    if fallback:
                        realtime_translation = fallback
                        await on_translate_final(fallback)

                raw_pcm_chunks.clear()
                utterance_buffer.clear()
                translate_buffer.clear()
                if stt_client:
                    stt_client.reset_buffer()
                if translate_client:
                    translate_client.reset_buffer()

                if current:
                    await orchestrator.handle_utterance(current, final_text, text_en=realtime_translation or None)
                
            elif msg_type == "intro.spoken":
                # 오프닝 인사는 응답자 화면이 자체적으로 만들어 발화한다.
                # 백엔드를 거치지 않다 보니 참관자 대시보드에는 인터뷰가
                # 아무 말 없이 시작한 것처럼 보였고, 기록에도 남지 않았다.
                # 실제로 발화한 텍스트를 받아 AI 진행자 턴으로 기록한다.
                intro_text = (message.get("text") or "").strip()
                if not intro_text:
                    continue
                current = await store.get_session(session_id)
                if current is None:
                    continue
                await orchestrator.record_assistant_intro(current, intro_text)

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
