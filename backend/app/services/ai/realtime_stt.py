import asyncio
import json
import logging
import base64
from typing import AsyncGenerator, Callable
import websockets

from app.core.config import get_settings

logger = logging.getLogger(__name__)

class RealtimeSTTClient:
    def __init__(self, session_id: str, deployment: str, on_partial_transcript: Callable, on_final_transcript: Callable):
        self.session_id = session_id
        self.deployment = deployment
        self.settings = get_settings()
        self.on_partial = on_partial_transcript
        self.on_final = on_final_transcript
        self.ws = None
        self.running = False
        self.current_text = ""

    async def connect(self):
        """Azure OpenAI Realtime 웹소켓 연결 (Whisper / Translate)"""
        endpoint = self.settings.azure_openai_endpoint.replace("https://", "wss://").rstrip("/")
        api_key = self.settings.azure_openai_api_key
        
        # Realtime API websocket URL 형식
        url = f"{endpoint}/openai/realtime?api-version={self.settings.azure_openai_api_version}&deployment={self.deployment}"
        
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
            
            # Determine system prompt based on deployment
            system_prompt = "You are a helpful assistant."
            if "translate" in self.deployment:
                system_prompt = "You are a real-time translator. Translate whatever the user says into English. Output ONLY the English translation without any conversational filler."
            else:
                system_prompt = "You are a real-time transcriber. Transcribe whatever the user says in Korean. Output ONLY the Korean transcription without any conversational filler."

            # 세션 초기화 (Text 모드로 설정)
            update_payload = {
                "type": "session.update",
                "session": {
                    "modalities": ["text"],
                    "instructions": system_prompt,
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 500
                    },
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
                
                if msg_type == "response.text.delta":
                    delta = data.get("delta", "")
                    self.current_text += delta
                    # logger.info(f"[{self.session_id}] STT 조각: {delta} -> 누적: {self.current_text}")
                    await self.on_partial(self.current_text)
                elif msg_type == "response.text.done":
                    text = data.get("text", "")
                    if text:
                        self.current_text = text
                    logger.info(f"[{self.session_id}] STT 완료: {self.current_text}")
                    await self.on_final(self.current_text)
                    self.current_text = ""
                elif msg_type == "conversation.item.input_audio_transcription.partial":
                    # Some implementations emit this
                    text = data.get("transcript", "")
                    logger.info(f"[{self.session_id}] STT Transcription Partial: {text}")
                    await self.on_partial(text)
                elif msg_type == "conversation.item.input_audio_transcription.completed":
                    # Fallback for input audio transcription if enabled
                    text = data.get("transcript", "")
                    logger.info(f"[{self.session_id}] STT Transcription Completed: {text}")
                    if "translate" not in self.deployment:
                        await self.on_final(text)
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
        
        # Audio chunk 전송
        await self.ws.send(json.dumps({
            "type": "input_audio_buffer.append",
            "audio": base64_pcm
        }))

    async def commit_audio(self):
        if not self.running or not self.ws:
            return
        
        logger.info(f"[{self.session_id}] 마이크 끄기 - 발화 종료 신호(commit/create) 전송")
        # 발화 종료 신호
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
