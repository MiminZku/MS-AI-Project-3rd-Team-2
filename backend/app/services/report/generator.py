"""세션 종료 시 이 generate()가 호출된다 (services/orchestrator.py의 end_session 참고).

담당자 작업 지점: 이 함수 전체.
session/transcript를 가지고 원하는 방식으로 분석해서 Report(data=...)로 반환하면 된다.
data의 형식은 자유 — JSON 필드 구성이든, 텍스트 요약이든, 렌더링한 HTML 문자열이든 제약 없음.
개발 중 빠르게 반복하려면 더미 데이터를 쓸 것: backend/dummy_data/interview_codex_vs_claude.json
(로드 방법은 README나 팀 채팅 참고)

저장/조회는 이미 연결되어 있어 이 함수만 채우면 전체 흐름이 동작한다:
  - 트리거: orchestrator.py의 end_session()이 세션 종료 시 백그라운드로 호출
  - 저장:   store.py의 save_report/get_report (Redis 또는 인메모리)
  - 조회:   GET /api/sessions/{id}/report
"""

from __future__ import annotations

from app.schemas.report import Report
from app.schemas.session import Session, Turn


async def generate(session: Session, transcript: list[Turn]) -> Report:
    # TODO(담당자): 여기부터 구현. 지금은 아무 분석도 하지 않는 placeholder.
    return Report(
        session_id=session.id,
        data={"status": "not_implemented", "turn_count": len(transcript)},
    )
