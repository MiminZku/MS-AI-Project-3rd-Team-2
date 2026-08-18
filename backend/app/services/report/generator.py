from __future__ import annotations

from app.schemas.report import Report
from app.schemas.session import Instruction, Session, Turn
from app.schemas.study import ResearchStudy
from app.services.report.analyzer import get_report_analyzer
from app.services.store import get_store


async def generate(
    session: Session,
    transcript: list[Turn],
    instructions: list[Instruction],
) -> Report:

    # =====================================================
    # 1. Session에 연결된 ResearchStudy 조회
    # =====================================================

    study: ResearchStudy | None = None

    if session.study_id:
        study = await get_store().get_study(
            session.study_id
        )

        if study is None:
            raise ValueError(
                "Session에 연결된 ResearchStudy를 "
                f"찾을 수 없습니다: {session.study_id}"
            )

    # =====================================================
    # 2. 실제 응답자 발언만 추출
    # =====================================================

    interviewee_turns = [
        turn
        for turn in transcript
        if turn.speaker == "interviewee"
    ]

    # =====================================================
    # 3. Evidence Library 생성
    # =====================================================

    evidence = []

    for number, turn in enumerate(
        interviewee_turns,
        start=1,
    ):
        evidence.append(
            {
                "evidence_id": f"E{number:03d}",
                "turn_index": turn.index,
                "speaker": turn.speaker,
                "quote": turn.text,
                "created_at": (
                    turn.created_at.isoformat()
                ),
            }
        )

    # =====================================================
    # 4. Observer Intervention 기록
    # =====================================================

    observer_interventions = []

    for instruction in instructions:
        observer_interventions.append(
            {
                "instruction_id": instruction.id,
                "instruction": instruction.text,
                "status": instruction.status,
                "applied_turn": instruction.applied_turn,
                "created_at": (
                    instruction.created_at.isoformat()
                ),
                "applied_at": (
                    instruction.applied_at.isoformat()
                    if instruction.applied_at
                    else None
                ),
            }
        )

    # =====================================================
    # 5. AI Analyzer 호출
    #
    # 핵심:
    # 이제 Analyzer가 하드코딩 Slot이 아니라
    # 이 Session에 연결된 Study 자체를 받는다.
    # =====================================================

    analyzer = get_report_analyzer()

    analysis = await analyzer.analyze(
        session=session,
        transcript=transcript,
        instructions=instructions,
        study=study,
    )

    # =====================================================
    # 6. 실제 Evidence / Observer 데이터 합치기
    # =====================================================

    analysis["observer_interventions"] = (
        observer_interventions
    )

    analysis["evidence"] = evidence

    # =====================================================
    # 7. Metadata
    # =====================================================

    analysis["metadata"] = {
        "study_id": (
            study.id
            if study
            else None
        ),
        "research_title": (
            study.title
            if study
            else session.title
        ),
        "duration_minutes": (
            session.duration_minutes
        ),
        "question_count": (
            len(session.questions)
        ),
        "information_slot_count": (
            len(study.information_slots)
            if study
            else 0
        ),
        "turn_count": len(transcript),
        "interviewee_turn_count": (
            len(interviewee_turns)
        ),
        "instruction_count": (
            len(instructions)
        ),
    }

    # =====================================================
    # 8. 최종 Report
    # =====================================================

    return Report(
        session_id=session.id,
        data=analysis,
    )