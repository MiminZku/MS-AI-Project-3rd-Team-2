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
        # _receive_loop 태스크 참조. 보관하지 않으면 GC 대상이 될 수 있고,
        # 재연결 시 이전 루프가 살아있는지 확인할 수도 없다.
        self._receive_task: asyncio.Task | None = None
        # 연결이 끊겨 오디오를 버린 횟수 — 조용히 죽는 것을 막기 위한 로그용
        self._dropped_chunks = 0

    def is_alive(self) -> bool:
        """수신 루프가 살아 있고 오디오를 보낼 수 있는 상태인지."""
        return bool(self.running and self.ws is not None)

    async def ensure_connected(self) -> bool:
        """끊겨 있으면 다시 연결한다.

        Realtime 세션은 턴이 끝나거나 유휴 상태가 되면 서버가 닫을 수 있다.
        예전에는 한 번 끊기면 running=False로 고정된 채 send_audio_chunk가
        조용히 무시돼서, 동시통역이 첫 발화 이후로 영영 멈춰 있었다.
        """
        if self.is_alive():
            return True

        logger.warning(
            f"[{self.session_id}] Realtime 세션이 끊겨 있어 재연결합니다 (Deployment: {self.deployment})"
        )

        # 남아 있는 소켓/태스크 정리 후 새로 연결
        await self.close()
        self.current_text = ""
        self._dropped_chunks = 0
        await self.connect()

        return self.is_alive()

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
            
            # 수신 루프 실행 (태스크 참조를 보관해 GC로 사라지지 않게 한다)
            self._receive_task = asyncio.create_task(self._receive_loop())
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
            # 여기서 끝나면 다음 발화부터는 오디오가 전송되지 않는다.
            # 다음 audio.start에서 ensure_connected()가 다시 붙여준다.
            logger.warning(
                f"[{self.session_id}] Realtime 웹소켓 닫힘 (Deployment: {self.deployment}) "
                "— 다음 발화 시작 시 재연결합니다."
            )
        except Exception:
            logger.exception(f"[{self.session_id}] 수신 루프 에러 (Deployment: {self.deployment})")
        finally:
            self.running = False

    async def send_audio_chunk(self, base64_pcm: str):
        if not self.is_alive():
            # 조용히 버리면 "동시통역이 갑자기 안 된다"로만 보인다. 주기적으로 남긴다.
            self._dropped_chunks += 1
            if self._dropped_chunks % 50 == 1:
                logger.warning(
                    f"[{self.session_id}] 연결이 끊겨 오디오 청크를 버리는 중 "
                    f"({self._dropped_chunks}개, Deployment: {self.deployment})"
                )
            return

        event_type = "session.input_audio_buffer.append" if "translate" in self.deployment else "input_audio_buffer.append"
        try:
            await self.ws.send(json.dumps({
                "type": event_type,
                "audio": base64_pcm
            }))
        except Exception:
            # 전송 중 끊긴 경우에도 running을 내려 다음 턴에 재연결되게 한다.
            logger.warning(
                f"[{self.session_id}] 오디오 전송 실패 — 연결 해제 처리 (Deployment: {self.deployment})"
            )
            self.running = False

    async def commit_audio(self):
        if not self.is_alive():
            return

        logger.info(f"[{self.session_id}] 마이크 끄기 - 발화 종료 신호 전송")
        if "translate" in self.deployment:
            # Translate 세션에서는 별도의 response.create 없이 지속적으로 스트리밍 처리됨
            return

        try:
            await self.ws.send(json.dumps({
                "type": "input_audio_buffer.commit"
            }))
            await self.ws.send(json.dumps({
                "type": "response.create"
            }))
        except Exception:
            logger.warning(
                f"[{self.session_id}] 발화 종료 신호 전송 실패 — 연결 해제 처리 "
                f"(Deployment: {self.deployment})"
            )
            self.running = False

    def reset_buffer(self):
        """턴 전환 시 이전 발화 버퍼 초기화."""
        self.current_text = ""

    async def close(self):
        self.running = False

        task = self._receive_task
        self._receive_task = None
        if task is not None and not task.done():
            task.cancel()

        ws = self.ws
        self.ws = None
        if ws is not None:
            try:
                await ws.close()
            except Exception:
                logger.debug(f"[{self.session_id}] 웹소켓 종료 중 예외 (무시)")

