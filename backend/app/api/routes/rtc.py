import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Literal

from app.core.config import get_settings

router = APIRouter(prefix="/sessions/{session_id}/rtc", tags=["rtc"])

class RtcTokenRequest(BaseModel):
    role: Literal["interviewee", "observer"]

class RtcTokenResponse(BaseModel):
    user_id: str
    token: str
    expires_on: str
    group_id: str

@router.post("/token", response_model=RtcTokenResponse)
async def create_rtc_token(session_id: str, request: RtcTokenRequest):
    """
    해당 세션의 화상 통화(WebRTC) 방에 접속하기 위한 ACS 접속 토큰을 발급합니다.
    - role: "interviewee" (마이크/비디오 송출 가능) 또는 "observer" (수신 전용 권한 권장)
    """
    settings = get_settings()

    try:
        # ACS 그룹 통화는 반드시 표준 UUID를 groupId로 요구하므로, session_id 기반으로 결정론적 UUID를 생성
        group_id = str(uuid.uuid5(uuid.NAMESPACE_URL, session_id))

        if settings.environment == "local" and not settings.acs_connection_string:
            return RtcTokenResponse(user_id="dummy", token="dummy", expires_on="dummy", group_id=group_id)
        if not settings.acs_connection_string:
            raise HTTPException(status_code=500, detail="ACS_CONNECTION_STRING is not configured in backend.")

        from azure.communication.identity.aio import CommunicationIdentityClient
        async with CommunicationIdentityClient.from_connection_string(settings.acs_connection_string) as client:
            user = await client.create_user()
            token_response = await client.get_token(user, scopes=["voip"])
            
            return RtcTokenResponse(
                user_id=user.properties['id'],
                token=token_response.token,
                expires_on=str(token_response.expires_on),
                group_id=group_id
            )
    except ImportError:
        raise HTTPException(status_code=500, detail="azure-communication-identity is not installed.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
