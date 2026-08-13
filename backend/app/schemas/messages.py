"""WebSocket 메시지 계약.

프론트엔드(frontend/*/src/types.ts)와 이 파일을 항상 같이 수정할 것.

인터뷰이 채널 (/ws/interview/{session_id})
  C -> S : utterance            응답자 발화 텍스트 (STT 연결 전에는 수동 입력)
  S -> C : session.state        접속 직후 세션 상태
  S -> C : assistant.question   AI 진행자의 다음 질문 (rationale 절대 미포함, C5)
  S -> C : error

참관자 채널 (/ws/observer/{session_id})
  C -> S : instruction.create   지시 입력
  S -> C : session.snapshot     접속 직후 세션 + 대화기록 + 지시이력
  S -> C : transcript.append    새 턴 (assistant 턴은 rationale 포함)
  S -> C : instruction.queued   큐 적재됨
  S -> C : instruction.applied  다음 질문에 주입 완료 (ack)
  S -> C : timekeeper.signal    타임키퍼 주제 전환 신호
  S -> C : session.ended        세션 종료 (관리자가 종료 버튼 클릭)
  S -> C : report.ready         AI 리포트 생성 완료 (§4.4, D6). GET /api/sessions/{id}/report로도 조회 가능
  S -> C : error
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

InterviewClientMessageType = Literal["utterance"]
ObserverClientMessageType = Literal["instruction.create"]


class ClientMessage(BaseModel):
    """양쪽 채널의 수신 메시지 공통 형태."""

    type: str
    text: str = ""


def server_message(type_: str, **payload: Any) -> dict[str, Any]:
    return {"type": type_, **payload}
