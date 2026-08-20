import asyncio
import json
import logging
import base64
from typing import AsyncGenerator, Callable
import websockets

from app.core.config import get_settings

logger = logging.getLogger(__name__)

class RealtimeSTTClient:
    def __init__(
        self,
        session_id: str,
        deployment: str,
        on_partial_transcript: Callable,
        on_final_transcript: Callable,
        source_lang: str = "Korean",
        target_lang: str = "English"
    ):
        self.session_id = session_id
        self.deployment = deployment
        self.settings = get_settings()
        self.on_partial = on_partial_transcript
        self.on_final = on_final_transcript
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.ws = None
        self.running = False
        self.current_text = ""

    async def connect(self):
        """Azure OpenAI Realtime 웹소켓 연결 (Whisper / Translate)"""
        endpoint = self.settings.azure_openai_endpoint.replace("https://", "wss://").rstrip("/")
        api_key = self.settings.azure_openai_api_key
        
        # Azure OpenAI Realtime API (GA 표준 엔드포인트)
        is_translate = "translate" in self.deployment
        path = "/openai/v1/realtime/translations" if is_translate else "/openai/v1/realtime"
        url = f"{endpoint}{path}?model={self.deployment}"
        
        headers = {
            "api-key": api_key
        }

        try:
            logger.info(f"[{self.session_id}] 실시간 STT 웹소켓 연결 시도 중 (Deployment: {self.deployment})...")
            try:
                self.ws = await websockets.connect(url, additional_headers=headers)
                logger.info(f"[{self.session_id}] 실시간 STT 연결 성공 (websockets 14+ API)")
            except TypeError:
                self.ws = await websockets.connect(url, extra_headers=headers)
                logger.info(f"[{self.session_id}] 실시간 STT 연결 성공 (websockets Legacy API)")
            self.running = True
            
            # 세션 초기화 (Translate 엔드포인트와 일반 Realtime 엔드포인트 분기)
            if is_translate:
                target_code = "en"
                t_lower = self.target_lang.lower()
                if "ko" in t_lower or "korean" in t_lower:
                    target_code = "ko"
                elif "ja" in t_lower or "japanese" in t_lower:
                    target_code = "ja"
                elif "zh" in t_lower or "chinese" in t_lower:
                    target_code = "zh"
                elif "es" in t_lower or "spanish" in t_lower:
                    target_code = "es"

                update_payload = {
                    "type": "session.update",
                    "session": {
                        "audio": {
                            "output": {
                                "language": target_code
                            }
                        }
                    }
                }
            else:
                instructions = f"You are a real-time transcriber. Transcribe whatever the user says in {self.source_lang}. Output ONLY the {self.source_lang} transcription without any conversational filler."
                update_payload = {
                    "type": "session.update",
                    "session": {
                        "modalities": ["text"],
                        "instructions": instructions,
                        "input_audio_format": "pcm16",
                        "output_audio_format": "pcm16",
                        "input_audio_transcription": {
                            "model": "whisper-1"
                        }
                    }
                }

            logger.info(f"[{self.session_id}] 전송: session.update ({self.deployment})")
            await self.ws.send(json.dumps(update_payload))
            
            # 수신 루프 실행
            asyncio.create_task(self._receive_loop())
        except Exception as e:
            logger.exception(f"[{self.session_id}] 실시간 STT 연결 중 에러 발생: {e}")
            self.running = False

    async def _receive_loop(self):
        try:
            while self.running and self.ws:
                message = await self.ws.recv()
                data = json.loads(message)
                
                msg_type = data.get("type")
                
                # 너무 많은 delta 로그 방지 (선택적)
                if msg_type not in ["response.audio.delta", "input_audio_buffer.append"]:
                    logger.info(f"[{self.session_id}] 수신 이벤트: {msg_type}")
                
                # 수신 이벤트 처리
                if msg_type in ["response.text.delta", "session.output_transcript.delta", "response.audio_transcript.delta"]:
                    delta = data.get("delta", "")
                    self.current_text += delta
                    await self.on_partial(self.current_text)
                elif msg_type in ["response.text.done", "session.output_transcript.completed"]:
                    text = data.get("text", "") or self.current_text
                    logger.info(f"[{self.session_id}] 번역/전사 완료: {text}")
                    await self.on_final(text)
                    self.current_text = ""
                elif msg_type in ["conversation.item.input_audio_transcription.partial", "session.input_transcript.delta"]:
                    delta = data.get("transcript", "") or data.get("delta", "")
                    self.current_text += delta
                    await self.on_partial(self.current_text)
                elif msg_type in ["conversation.item.input_audio_transcription.completed", "session.input_transcript.completed"]:
                    text = data.get("transcript", "") or self.current_text
                    logger.info(f"[{self.session_id}] 한국어 전사 완료: {text}")
                    await self.on_final(text)
                    self.current_text = ""
                elif msg_type == "error":
                    logger.error(f"[{self.session_id}] Realtime API 에러: {data}")
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"[{self.session_id}] STT 웹소켓 닫힘 (정상 또는 서버측 끊김)")
        except Exception as e:
            logger.exception(f"[{self.session_id}] 수신 루프 에러")
        finally:
            self.running = False

    async def send_audio_chunk(self, base64_pcm: str):
        if not self.running or not self.ws:
            return
        
        event_type = "session.input_audio_buffer.append" if "translate" in self.deployment else "input_audio_buffer.append"
        await self.ws.send(json.dumps({
            "type": event_type,
            "audio": base64_pcm
        }))

    async def commit_audio(self):
        if not self.running or not self.ws:
            return
        
        logger.info(f"[{self.session_id}] 마이크 끄기 - 발화 종료 신호 전송")
        if "translate" in self.deployment:
            # Translate 세션에서는 별도의 response.create 없이 지속적으로 스트리밍 처리됨
            pass
        else:
            await self.ws.send(json.dumps({
                "type": "input_audio_buffer.commit"
            }))
            await self.ws.send(json.dumps({
                "type": "response.create"
            }))

    async def close(self):
        self.running = False
        if self.ws:
            await self.ws.close()
