from __future__ import annotations

from app.schemas.report import Report
from app.schemas.session import Instruction, Session, Turn
from app.services.report.analyzer import get_report_analyzer


async def generate(
    session: Session,
    transcript: list[Turn],
    instructions: list[Instruction],
) -> Report:

    # 1. 실제 응답자 발언만 추출
    interviewee_turns = [
        turn
        for turn in transcript
        if turn.speaker == "interviewee"
    ]

    # 2. Evidence Library 생성
    evidence = []

    for number, turn in enumerate(interviewee_turns, start=1):
        evidence.append(
            {
                "evidence_id": f"E{number:03d}",
                "turn_index": turn.index,
                "speaker": turn.speaker,
                "quote": turn.text,
                "created_at": turn.created_at.isoformat(),
            }
        )

    # 3. 참관자 개입 기록
    observer_interventions = []

    for instruction in instructions:
        observer_interventions.append(
            {
                "instruction_id": instruction.id,
                "instruction": instruction.text,
                "status": instruction.status,
                "applied_turn": instruction.applied_turn,
                "created_at": instruction.created_at.isoformat(),
                "applied_at": (
                    instruction.applied_at.isoformat()
                    if instruction.applied_at
                    else None
                ),
            }
        )

    # 4. 인터뷰 분석기 호출
    analyzer = get_report_analyzer()

    analysis = await analyzer.analyze(
        session=session,
        transcript=transcript,
        instructions=instructions,
    )

    # 5. AI 분석 결과 + 실제 근거 데이터 합치기
    analysis["observer_interventions"] = observer_interventions
    analysis["evidence"] = evidence

    analysis["metadata"] = {
        "research_title": session.title,
        "duration_minutes": session.duration_minutes,
        "question_count": len(session.questions),
        "turn_count": len(transcript),
        "interviewee_turn_count": len(interviewee_turns),
        "instruction_count": len(instructions),
    }

    # 6. 최종 Report 반환
    return Report(
        session_id=session.id,
        data=analysis,
    )