import httpx
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/avatar", tags=["avatar"])


class AvatarTokenResponse(BaseModel):
    token: str | None = None
    ice_servers: list[dict[str, Any]] = []
    region: str
    character: str = "lisa"
    style: str = "casual-sitting"
    voice: str = "ko-KR-SunHiNeural"


class CreateAvatarSessionRequest(BaseModel):
    sdp_offer: str
    character: str = "lisa"
    style: str = "casual-sitting"
    voice: str = "ko-KR-SunHiNeural"


class CreateAvatarSessionResponse(BaseModel):
    session_id: str
    sdp_answer: str


class SpeakRequest(BaseModel):
    text: str
    voice: str = "ko-KR-SunHiNeural"


@router.get("/relay-token", response_model=AvatarTokenResponse)
@router.post("/relay-token", response_model=AvatarTokenResponse)
async def get_avatar_relay_token():
    """
    Azure Speech Service의 Real-time Avatar Relay Token 및 ICE Server 정보를 발급받아 반환합니다.
    """
    settings = get_settings()

    if not settings.azure_speech_key or not settings.azure_speech_region:
        raise HTTPException(
            status_code=500,
            detail="AZURE_SPEECH_KEY 또는 AZURE_SPEECH_REGION이 백엔드 .env에 설정되지 않았습니다."
        )

    url = f"https://{settings.azure_speech_region}.tts.speech.microsoft.com/cognitiveservices/avatar/relay/token/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": settings.azure_speech_key
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"Azure Avatar Relay Token 요청 실패: {resp.text}"
                )
            
            data = resp.json()
            urls = data.get("Urls") or data.get("urls") or []
            username = data.get("Username") or data.get("username")
            credential = data.get("Password") or data.get("password")
            token = data.get("Token") or data.get("token")

            ice_servers = []
            if urls:
                server_obj: dict[str, Any] = {"urls": urls}
                if username:
                    server_obj["username"] = username
                if credential:
                    server_obj["credential"] = credential
                ice_servers.append(server_obj)

            return AvatarTokenResponse(
                token=token,
                ice_servers=ice_servers,
                region=settings.azure_speech_region,
                character="lisa",
                style="casual-sitting",
                voice="ko-KR-SunHiNeural"
            )
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Azure Speech Service 통신 오류: {str(e)}")


@router.post("/session", response_model=CreateAvatarSessionResponse)
async def create_avatar_session(request: CreateAvatarSessionRequest):
    """
    클라이언트의 SDP Offer를 Azure Speech Avatar WebRTC 엔드포인트에 전달하여
    세션을 시작하고 Answer SDP를 받아옵니다.
    """
    settings = get_settings()

    if not settings.azure_speech_key or not settings.azure_speech_region:
        raise HTTPException(
            status_code=500,
            detail="AZURE_SPEECH_KEY 또는 AZURE_SPEECH_REGION이 백엔드 .env에 설정되지 않았습니다."
        )

    url = f"https://{settings.azure_speech_region}.tts.speech.microsoft.com/cognitiveservices/avatar/webrtc/sessions?api-version=2024-04-15-preview"
    headers = {
        "Ocp-Apim-Subscription-Key": settings.azure_speech_key,
        "Content-Type": "application/json"
    }
    payload = {
        "sessionDescription": {
            "type": "offer",
            "sdp": request.sdp_offer
        },
        "avatar": {
            "character": request.character,
            "style": request.style,
            "video": {
                "codec": "vp8",
                "bitrate": 2000000,
                "crop": {
                    "topLeft": [0, 0],
                    "bottomRight": [1920, 1080]
                }
            }
        },
        "voice": {
            "name": request.voice
        }
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code not in (200, 201):
                logger.error(f"Avatar 세션 생성 실패: {resp.status_code} {resp.text}")
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"Azure Avatar 세션 생성 실패: {resp.text}"
                )

            data = resp.json()
            session_id = data.get("id") or data.get("sessionId")
            session_desc = data.get("sessionDescription", {})
            sdp_answer = session_desc.get("sdp") or ""

            return CreateAvatarSessionResponse(
                session_id=session_id,
                sdp_answer=sdp_answer
            )
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Azure Avatar 세션 생성 네트워크 오류: {str(e)}")


@router.post("/session/{avatar_session_id}/speak")
async def speak_avatar_session(avatar_session_id: str, request: SpeakRequest):
    """
    실행 중인 Azure Avatar WebRTC 세션에 텍스트 발화(TTS & 입모양)를 명령합니다.
    """
    settings = get_settings()

    if not settings.azure_speech_key or not settings.azure_speech_region:
        raise HTTPException(
            status_code=500,
            detail="AZURE_SPEECH_KEY 또는 AZURE_SPEECH_REGION이 백엔드 .env에 설정되지 않았습니다."
        )

    url = f"https://{settings.azure_speech_region}.tts.speech.microsoft.com/cognitiveservices/avatar/webrtc/sessions/{avatar_session_id}/speak?api-version=2024-04-15-preview"
    headers = {
        "Ocp-Apim-Subscription-Key": settings.azure_speech_key,
        "Content-Type": "application/json"
    }
    payload = {
        "text": request.text,
        "voice": request.voice
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code not in (200, 204):
                logger.error(f"Avatar 발화 명령 실패: {resp.status_code} {resp.text}")
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"Azure Avatar 발화 명령 실패: {resp.text}"
                )
            return {"status": "success", "session_id": avatar_session_id, "text": request.text}
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Azure Avatar 발화 네트워크 오류: {str(e)}")


@router.delete("/session/{avatar_session_id}")
async def stop_avatar_session(avatar_session_id: str):
    """
    아바타 WebRTC 세션을 종료합니다.
    """
    settings = get_settings()
    url = f"https://{settings.azure_speech_region}.tts.speech.microsoft.com/cognitiveservices/avatar/webrtc/sessions/{avatar_session_id}?api-version=2024-04-15-preview"
    headers = {
        "Ocp-Apim-Subscription-Key": settings.azure_speech_key
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.delete(url, headers=headers)
            return {"status": "stopped"}
    except Exception:
        return {"status": "stopped"}
