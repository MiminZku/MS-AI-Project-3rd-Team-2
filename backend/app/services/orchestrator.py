"""핑퐁 루프 오케스트레이션 (§3 ①~⑥).

응답자 발화 1건이 들어오면:
  ③ 지시 큐에서 1건 pop (없으면 스킵)          <- D2 큐 소진형
  ④ 프롬프트 조립 (지시 은밀 주입)
  ⑤ GPT-4o가 다음 질문 + 판단 근거 생성
  ⑥ 인터뷰이에게 질문 전송 / 참관자에게 근거 포함 전송

인터뷰 종료 후:
  ① 개별 인터뷰 Report 생성
  ② 같은 Study의 Session 상태 확인
  ③ 모든 Session이 종료되고 개별 Report가 준비되면
  ④ StudyReportAnalyzer로 종합 분석
  ⑤ study_report.json 저장
  ⑥ Word / Power BI Excel 자동 생성
  ⑦ Azure Blob Storage reports 컨테이너 자동 업로드
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from app.export_study_report_bi import (
    main as export_powerbi_dataset,
)
from app.export_study_report_word import (
    main as export_word_report,
)
from app.schemas.messages import server_message
from app.schemas.session import (
    Instruction,
    Session,
    Turn,
    utcnow,
)
from app.services.ai import timekeeper
from app.services.ai.llm import GeneratedQuestion, get_question_generator
from app.services.connections import manager
from app.services.respondent_session_state import (
    build_respondent_session_state,
)
from app.services.report import generator as report_generator
from app.services.report.study_analyzer import (
    get_study_report_analyzer,
)
from app.services.store import (
    Store,
    ack_instruction,
    get_store,
)


logger = logging.getLogger(__name__)


# =========================================================
# Study Report 출력 경로
# =========================================================

APP_DIR = Path(__file__).resolve().parents[1]

REPORT_DIR = (
    APP_DIR
    / "ai-interview-report"
)

STUDY_REPORT_JSON_PATH = (
    REPORT_DIR
    / "study_report.json"
)


# =========================================================
# Study별 동시 종합 분석 방지 Lock
#
# 여러 인터뷰가 거의 동시에 종료되었을 때
# 같은 Study 종합 분석이 중복 실행되는 것을 막는다.
#
# 현재 프로세스 내부 Lock이다.
# 추후 멀티 인스턴스 배포 시 Redis Lock 등으로 교체 가능.
# =========================================================

_study_report_locks: dict[
    str,
    asyncio.Lock,
] = {}


# =========================================================
# Study 출력 파일 전역 Lock
#
# 현재 Word / Power BI Exporter는 공통 경로의
# study_report.json / docx / xlsx를 사용한다.
# 서로 다른 Study가 동시에 종료되면 파일이 섞일 수 있으므로
# JSON 저장 → Export → Blob 업로드 구간은 한 번에 하나만 실행한다.
# =========================================================

_study_output_lock = asyncio.Lock()


def _get_study_report_lock(
    study_id: str,
) -> asyncio.Lock:

    lock = _study_report_locks.get(
        study_id
    )

    if lock is None:

        lock = asyncio.Lock()

        _study_report_locks[
            study_id
        ] = lock

    return lock


# =========================================================
# Turn Payload
# =========================================================

def _turn_payload(
    turn: Turn,
    *,
    for_observer: bool,
) -> dict:
    """
    C5:
    판단 근거(rationale)는
    참관자 페이로드에만 포함한다.
    """

    data = turn.model_dump(
        mode="json"
    )

    if not for_observer:
        data.pop(
            "rationale",
            None,
        )

    return data


# =========================================================
# 인터뷰 발화 처리
# =========================================================

async def handle_utterance(
    session: Session,
    text: str,
    *,
    text_en: str | None = None,
) -> None:

    store = get_store()

    # 이미 종료된 세션에서는 어떤 경로로 발화가 더 들어와도 새 질문을 만들지 않는다.
    # (자동 종료 직후 응답자 마이크가 한 번 더 열려 있는 경우 등)
    if session.status == "ended":
        logger.info(
            "종료된 세션의 발화 무시 session=%s",
            session.id,
        )
        return

    # -----------------------------------------------------
    # ① 응답자 발화 기록
    # -----------------------------------------------------

    index = await store.next_turn_index(
        session.id
    )

    user_turn = Turn(
        index=index,
        speaker="interviewee",
        text=text,
        text_en=text_en,
    )

    await store.append_turn(
        session.id,
        user_turn,
    )

    await manager.broadcast_to_observers(
        session.id,
        server_message(
            "transcript.append",
            turn=_turn_payload(
                user_turn,
                for_observer=True,
            ),
        ),
    )

    # -----------------------------------------------------
    # ③ 지시 큐에서 1건 pop
    #
    # LPOP 자체가 ack이므로
    # 재주입되지 않는다 (C4).
    # -----------------------------------------------------

    instruction: Instruction | None = (
        await store.pop_instruction(
            session.id
        )
    )

    # -----------------------------------------------------
    # ④⑤ 프롬프트 조립 + 다음 질문 생성
    # -----------------------------------------------------

    transcript = (
        await store.get_transcript(
            session.id
        )
    )

    generator = (
        get_question_generator()
    )

    generated = (
        await generator.generate(
            session=session,
            transcript=transcript,
            instruction=instruction,
            timekeeper_hint=(
                timekeeper.latest_hint(
                    session.id
                )
            ),
        )
    )

    assistant_turn = Turn(
        index=index + 1,
        speaker="assistant",
        text=generated.text,
        rationale=generated.rationale,
        instruction_id=(
            instruction.id
            if instruction
            else None
        ),
    )

    await store.append_turn(
        session.id,
        assistant_turn,
    )

    # -----------------------------------------------------
    # 질문 트리 진행 위치 및 상태 머신 갱신
    # -----------------------------------------------------
    curr_idx = session.current_question_index
    total_q = len(session.questions)

    # 이번 턴에 모델이 해야 했던 일이 "아직 묻지 않은 메인 질문 전달"이었는지.
    # 이 경우 방금 들어온 응답자 발화는 현재 질문이 아니라 그 직전 질문(또는 인사말)에 대한 답변이다.
    pending_main = curr_idx < total_q and not session.main_question_asked

    # 음성인식 오류가 의심되는 턴(needs_clarification)에서는 애초에 신뢰할 수 없는 텍스트에서
    # 나온 결과이므로, 사실/분기 정보를 기록하지 않는다 — 잘못 들은 내용이 covered_facts에
    # 박제되어 이후 프롬프트에 "이미 확보된 사실"인 양 계속 노출되는 것을 막기 위함.
    if not generated.needs_clarification:
        # 획득한 사실(Fact) 업데이트.
        # pending_main 턴의 발화는 직전 질문에 대한 답변이므로 한 칸 앞 인덱스에 귀속시킨다.
        # (curr_idx == 0 이면 인터뷰 첫 인사말이라 귀속시킬 질문이 없다.)
        if generated.extracted_fact:
            fact_index = curr_idx - 1 if pending_main else curr_idx
            if fact_index >= 0:
                session.covered_facts[f"질문_{fact_index + 1}"] = generated.extracted_fact

        # 파생질문(Branch) 추적
        if generated.selected_branch:
            session.active_branch = generated.selected_branch
            if generated.selected_branch not in session.taken_branches:
                session.taken_branches.append(generated.selected_branch)
        else:
            session.active_branch = None

    if instruction is not None:
        # 참관자 지시 턴은 대본 밖의 개입이다. 모델이 발화한 것은 지시 꼬리질문이지
        # 대본의 메인 질문이 아니므로, 진행 위치를 넘기지 않는다.
        # (넘겨버리면 다음 메인 질문을 아무도 묻지 않은 채 건너뛰게 된다.)
        session.probe_count += 1

    elif pending_main:
        # 이번 턴의 발화가 곧 메인 질문 전달이다. 아직 답변을 받기 전이므로 절대 전이하지 않는다.
        # 모델이 is_sufficient=True 나 next_question_index 증가를 보내와도 무시한다.
        # 단, 되묻기(needs_clarification)를 한 턴이면 메인 질문은 여전히 전달되지 않은 상태다.
        if not generated.needs_clarification:
            session.main_question_asked = True
        session.probe_count = 0
        session.active_branch = None

    else:
        # 답변 충족도 및 모델 판단에 따른 전이
        # 1) 답변이 충분하여 모델이 다음 질문으로 넘어가자고 판단했거나(is_sufficient=True 또는 next_question_index > curr_idx)
        #    혹은 비정상적 무한 루프 방지 안전 한도(probe_count >= 5)에 도달한 경우 -> 다음 메인 질문으로 전이
        #    단, needs_clarification(음성인식 오류 의심)인 턴은 안전 한도에 도달하기 전까지는 절대 전이하지 않는다 —
        #    잘못 들은 답변을 "충분하다"고 착각해 다음 질문으로 넘어가버리는 것을 막기 위한 조건.
        model_decided_advance = generated.is_sufficient or generated.next_question_index > curr_idx
        probe_limit_reached = session.probe_count >= 5

        if generated.needs_clarification and not probe_limit_reached:
            should_advance = False
        else:
            should_advance = model_decided_advance or probe_limit_reached

        if should_advance:
            if curr_idx not in session.completed_question_indices and curr_idx < total_q:
                session.completed_question_indices.append(curr_idx)
            session.current_question_index = min(curr_idx + 1, total_q)
            session.probe_count = 0
            session.active_branch = None
            # 모델이 스스로 전이를 택한 턴에서는 프롬프트 지침대로 이번 발화에 다음 메인 질문을
            # 그대로 물었다고 본다. 반면 probe 한도 초과로 강제 전이시킨 경우 모델의 발화는
            # 여전히 이전 질문의 꼬리질문이므로, 다음 메인 질문은 아직 전달되지 않았다.
            session.main_question_asked = model_decided_advance and not generated.needs_clarification
        else:
            # 2) 아직 탐색할 파생질문이 남아있거나 추가 확인이 필요한 경우(is_sufficient=False) -> 현재 질문 인덱스 유지 및 probe_count 증가
            session.probe_count += 1

    await store.save_session(
        session
    )

    # 대시보드 트리 UI 동기화를 위해 변경된 세션 상태 브로드캐스트
    msg = server_message(
        "session.state",
        session={
            "id": session.id,
            "title": session.title,
            "status": session.status,
            "duration_minutes": session.duration_minutes,
            "questions": [q.model_dump(mode="json") for q in session.questions],
            "current_question_index": session.current_question_index,
            "main_question_asked": session.main_question_asked,
            "completed_question_indices": session.completed_question_indices,
            "probe_count": session.probe_count,
            "active_branch": session.active_branch,
            "taken_branches": session.taken_branches,
        },
    )
    await manager.broadcast_to_observers(session.id, msg)

    # -----------------------------------------------------
    # ⑥ 인터뷰이에게는 질문만
    # -----------------------------------------------------

    await manager.send_to_interviewee(
        session.id,
        server_message(
            "assistant.question",
            turn=_turn_payload(
                assistant_turn,
                for_observer=False,
            ),
        ),
    )

    # -----------------------------------------------------
    # 참관자에게는 판단 근거 포함
    # -----------------------------------------------------

    await manager.broadcast_to_observers(
        session.id,
        server_message(
            "transcript.append",
            turn=_turn_payload(
                assistant_turn,
                for_observer=True,
            ),
        ),
    )

    # -----------------------------------------------------
    # 참관자 Instruction 적용 완료
    # -----------------------------------------------------

    if instruction is not None:

        applied = await ack_instruction(
            store,
            instruction,
            assistant_turn.index,
        )

        await manager.broadcast_to_observers(
            session.id,
            server_message(
                "instruction.applied",
                instruction=(
                    applied.model_dump(
                        mode="json"
                    )
                ),
            ),
        )

    # -----------------------------------------------------
    # ⑦ 작별 인사를 전달했다면 참관자가 종료 버튼을 누른 것과 동일하게 자동 종료
    # -----------------------------------------------------

    if await _should_auto_end(session, generated, store, instruction):

        logger.info(
            "AI 종료 멘트 후 세션 자동 종료 session=%s",
            session.id,
        )

        await end_session(session)


# =========================================================
# 자동 종료 판단
# =========================================================

async def _should_auto_end(
    session: Session,
    generated: GeneratedQuestion,
    store: Store,
    instruction: Instruction | None = None,
) -> bool:
    """AI가 작별 인사를 마쳤고, 더 진행할 것이 남아있지 않은지 판단한다.

    참관자가 종료 버튼을 누르는 것과 같은 효과이므로 조건을 보수적으로 잡는다.
    넷 중 하나라도 어긋나면 종료하지 않고 인터뷰를 계속한다.
    """

    # ① 모델이 이번 발화를 작별 인사로 신고했는가
    if not generated.is_closing:
        return False

    # ② 대본의 모든 질문을 마쳤는가
    #    (모델이 중간에 잘못 판단해 인터뷰를 조기 종료시키는 것을 막는 안전장치)
    if session.current_question_index < len(session.questions):
        return False

    # ③ 이번 턴이 방금 처리한 참관자 지시에 대한 응답은 아닌가
    #    참관자가 직접 개입해서 무언가 물어보라고 지시했는데, 모델이 그 응답을
    #    작별 인사로 마무리해버렸다고 해서 곧바로 세션을 끝내면 참관자 의도와 어긋난다.
    if instruction is not None:
        return False

    # ④ 대기 중인 참관자 지시가 없는가
    #    이번 턴에 소비된 지시는 위에서 이미 applied 처리됐으므로 queued에 잡히지 않는다.
    try:
        instructions = await store.list_instructions(session.id)
    except Exception:
        # 큐 조회에 실패했으면 남은 지시가 있는지 확신할 수 없으므로 자동 종료하지 않는다.
        logger.exception(
            "자동 종료 판단용 지시 큐 조회 실패 session=%s",
            session.id,
        )
        return False

    return not any(
        instruction.status == "queued"
        for instruction in instructions
    )


# =========================================================
# Session 시작 (PM 수동 시작 및 상태 브로드캐스트)
# =========================================================

async def start_session(
    session: Session,
    *,
    broadcast_observer_state: bool = True,
) -> Session:
    session.status = "running"
    session.started_at = utcnow()
    await get_store().save_session(session)

    # D5: 비동기 격리된 폴링 태스크 (C9)
    timekeeper.start(session.id)

    # 인터뷰이와 참관자에게 session.state 실시간 브로드캐스트
    respondent_message = server_message(
        "session.state",
        session=await build_respondent_session_state(session),
    )
    await manager.send_to_interviewee(session.id, respondent_message)
    if broadcast_observer_state:
        observer_message = server_message(
            "session.state",
            session={
                "id": session.id,
                "title": session.title,
                "status": session.status,
                "duration_minutes": session.duration_minutes,
                "questions": [q.model_dump(mode="json") for q in session.questions],
            },
        )
        await manager.broadcast_to_observers(session.id, observer_message)

    return session


async def start_session_if_needed(
    session: Session,
    *,
    broadcast_observer_state: bool = True,
) -> Session:

    if session.status == "created":
        return await start_session(
            session,
            broadcast_observer_state=broadcast_observer_state,
        )

    return session


# =========================================================
# Session 종료
# =========================================================

async def end_session(
    session: Session,
) -> Session:

    # 자동 종료와 참관자의 수동 종료가 겹칠 수 있다. 리포트가 두 번 생성되지 않도록
    # 이미 종료된 세션은 그대로 돌려준다.
    if session.status == "ended":
        return session

    session.status = "ended"

    session.ended_at = utcnow()

    await get_store().save_session(
        session
    )

    timekeeper.stop(
        session.id
    )

    await manager.broadcast_to_observers(
        session.id,
        server_message(
            "session.ended",
            session=(
                session.model_dump(
                    mode="json"
                )
            ),
        ),
    )

    # 인터뷰이에게도 종료 상태를 전파해야 메인룸이 종료 화면으로 전환된다.
    # 인터뷰이 클라이언트는 session.state 만 구독하므로 start_session 과 동일한 형식으로 보낸다.
    await manager.send_to_interviewee(
        session.id,
        server_message(
            "session.state",
            session={
                "id": session.id,
                "title": session.title,
                "status": session.status,
                "duration_minutes": session.duration_minutes,
                "questions": [q.model_dump(mode="json") for q in session.questions],
            },
        ),
    )

    # -----------------------------------------------------
    # D6:
    #
    # 별도 Azure Event Grid / Functions 없이
    # 백엔드 내부 비동기 태스크로 개별 리포트 생성.
    #
    # 종료 API 응답을 막지 않도록
    # fire-and-forget.
    # -----------------------------------------------------

    asyncio.create_task(
        _generate_report(
            session.id
        )
    )

    return session


# =========================================================
# 개별 인터뷰 Report 생성
# =========================================================

async def _generate_report(
    session_id: str,
) -> None:

    store = get_store()

    session = await store.get_session(
        session_id
    )

    if session is None:

        logger.warning(
            "리포트 생성 대상 Session 없음 "
            "session=%s",
            session_id,
        )

        return

    transcript = (
        await store.get_transcript(
            session_id
        )
    )

    instructions = (
        await store.list_instructions(
            session_id
        )
    )

    try:

        report = (
            await report_generator.generate(
                session,
                transcript,
                instructions,
            )
        )

    except Exception:

        logger.exception(
            "리포트 생성 실패 "
            "session=%s",
            session_id,
        )

        return

    # -----------------------------------------------------
    # 개별 Report 저장
    # -----------------------------------------------------

    await store.save_report(
        report
    )

    logger.info(
        "개별 리포트 생성 완료 "
        "session=%s study=%s",
        session.id,
        session.study_id,
    )

    # -----------------------------------------------------
    # 개별 Report 준비 알림
    # -----------------------------------------------------

    await manager.broadcast_to_observers(
        session_id,
        server_message(
            "report.ready",
            report=(
                report.model_dump(
                    mode="json"
                )
            ),
        ),
    )

    # -----------------------------------------------------
    # Legacy Session이면
    # Study 종합 분석 대상이 아니다.
    # -----------------------------------------------------

    if not session.study_id:
        return

    # -----------------------------------------------------
    # Study 종합 분석 가능 여부를
    # 별도 background task에서 확인.
    #
    # 개별 Report 생성 완료 이벤트가
    # 종합 리포트 트리거가 된다.
    # -----------------------------------------------------

    asyncio.create_task(
        _maybe_generate_study_report(
            session.study_id
        )
    )


# =========================================================
# Study Report 생성 가능 여부 판단
# =========================================================

async def _maybe_generate_study_report(
    study_id: str,
) -> None:

    lock = _get_study_report_lock(
        study_id
    )

    async with lock:

        store = get_store()

        # -------------------------------------------------
        # Study 확인
        # -------------------------------------------------

        study = await store.get_study(
            study_id
        )

        if study is None:

            logger.warning(
                "Study 종합 분석 실패: "
                "Study 없음 study=%s",
                study_id,
            )

            return

        # -------------------------------------------------
        # 해당 Study의 Session 전체 조회
        # -------------------------------------------------

        sessions = (
            await store.list_sessions(
                study_id
            )
        )

        if not sessions:

            logger.info(
                "Study 종합 분석 대기: "
                "Session 없음 study=%s",
                study_id,
            )

            return

        # -------------------------------------------------
        # 아직 진행 중인 Session이 있으면 기다린다.
        #
        # 인터뷰 하나 끝날 때마다
        # Study 전체 LLM 분석을 돌리지 않기 위함.
        # -------------------------------------------------

        unfinished_sessions = [
            session
            for session in sessions
            if session.status != "ended"
        ]

        if unfinished_sessions:

            logger.info(
                "Study 종합 분석 대기: "
                "종료되지 않은 Session %d개 "
                "study=%s",
                len(
                    unfinished_sessions
                ),
                study_id,
            )

            return

        # -------------------------------------------------
        # 모든 개별 Report 수집
        # -------------------------------------------------

        participant_reports: list[
            dict[str, Any]
        ] = []

        missing_report_sessions: list[
            str
        ] = []

        for session in sessions:

            report = (
                await store.get_report(
                    session.id
                )
            )

            if report is None:

                missing_report_sessions.append(
                    session.id
                )

                continue

            participant_reports.append(
                report.data
            )

        # -------------------------------------------------
        # Session은 종료됐지만
        # 아직 개별 Report가 생성 중이면 기다린다.
        #
        # 해당 개별 Report가 완료되면
        # _generate_report()에서 이 함수를 다시 호출한다.
        # -------------------------------------------------

        if missing_report_sessions:

            logger.info(
                "Study 종합 분석 대기: "
                "개별 Report 미완료 %d개 "
                "study=%s sessions=%s",
                len(
                    missing_report_sessions
                ),
                study_id,
                missing_report_sessions,
            )

            return

        if not participant_reports:

            logger.warning(
                "Study 종합 분석 실패: "
                "participant_reports 없음 "
                "study=%s",
                study_id,
            )

            return

        # -------------------------------------------------
        # Study Analyzer 실행
        # -------------------------------------------------

        analyzer = (
            get_study_report_analyzer()
        )

        try:

            study_report = (
                await analyzer.analyze(
                    study,
                    participant_reports,
                )
            )

        except Exception:

            logger.exception(
                "Study 종합 분석 실패 "
                "study=%s",
                study_id,
            )

            return

        # -------------------------------------------------
        # Study 출력 파일 처리
        #
        # 현재 Exporter가 공통 파일 경로를 사용하므로
        # 서로 다른 Study의 파일이 섞이지 않게 전역 Lock 안에서
        # JSON 저장 → Word/BI Export → Blob 업로드까지 연속 실행한다.
        # -------------------------------------------------

        async with _study_output_lock:

            # ---------------------------------------------
            # study_report.json 저장
            # ---------------------------------------------

            try:

                await asyncio.to_thread(
                    _save_study_report_json,
                    study_report.model_dump(
                        mode="json"
                    ),
                )

            except Exception:

                logger.exception(
                    "Study Report JSON 저장 실패 "
                    "study=%s",
                    study_id,
                )

                return

            logger.info(
                "Study 종합 분석 완료 "
                "study=%s participants=%d",
                study_id,
                len(participant_reports),
            )

            # ---------------------------------------------
            # Word + Power BI Excel 자동 Export
            # ---------------------------------------------

            export_succeeded = True

            try:

                await asyncio.to_thread(
                    _export_study_outputs
                )

            except Exception:

                export_succeeded = False

                # Study JSON 자체는 이미 정상 생성됐으므로
                # Word/Excel Export 실패가
                # Study 분석 결과까지 날리지 않도록 분리한다.
                logger.exception(
                    "Study Report Export 실패 "
                    "study=%s",
                    study_id,
                )

            # ---------------------------------------------
            # Azure Blob Storage 자동 업로드
            #
            # 세 파일이 모두 최신 상태로 생성된 경우에만 업로드한다.
            # Export가 실패했는데 이전 파일을 잘못 올리는 것을 방지한다.
            # ---------------------------------------------

            if export_succeeded:

                try:

                    await asyncio.to_thread(
                        _upload_study_outputs_to_blob
                    )

                    logger.info(
                        "Study Report Blob 업로드 완료 "
                        "study=%s",
                        study_id,
                    )

                except Exception:

                    # 로컬 Study Report 생성 자체는 성공했으므로
                    # Blob 업로드 실패만 별도로 기록한다.
                    logger.exception(
                        "Study Report Blob 업로드 실패 "
                        "study=%s",
                        study_id,
                    )

        # -------------------------------------------------
        # 참관자 알림
        # -------------------------------------------------

        for session in sessions:

            try:

                await manager.broadcast_to_observers(
                    session.id,
                    server_message(
                        "study_report.ready",
                        study_id=study_id,
                        participant_count=len(
                            participant_reports
                        ),
                    ),
                )

            except Exception:

                logger.exception(
                    "Study Report ready 알림 실패 "
                    "study=%s session=%s",
                    study_id,
                    session.id,
                )


# =========================================================
# Study Report JSON 저장
# =========================================================

def _save_study_report_json(
    data: dict[str, Any],
) -> None:

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # -----------------------------------------------------
    # 바로 원본 파일에 쓰다가 중간에 실패하면
    # JSON이 깨질 수 있으므로 임시 파일 후 replace.
    # -----------------------------------------------------

    temporary_path = (
        STUDY_REPORT_JSON_PATH
        .with_suffix(
            ".json.tmp"
        )
    )

    with temporary_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    temporary_path.replace(
        STUDY_REPORT_JSON_PATH
    )


# =========================================================
# Word + Power BI Export
# =========================================================

def _export_study_outputs() -> None:

    errors: list[str] = []

    # -----------------------------------------------------
    # Word
    # -----------------------------------------------------

    try:

        export_word_report()

    except Exception:

        errors.append(
            "Word"
        )

        logger.exception(
            "자동 Word Report Export 실패"
        )

    # -----------------------------------------------------
    # Power BI Excel
    # -----------------------------------------------------

    try:

        export_powerbi_dataset()

    except Exception:

        errors.append(
            "Power BI"
        )

        logger.exception(
            "자동 Power BI Dataset Export 실패"
        )

    # -----------------------------------------------------
    # 하나라도 실패하면 Blob 업로드 단계로 넘어가지 않도록
    # 호출자에게 실패를 전달한다.
    # -----------------------------------------------------

    if errors:

        raise RuntimeError(
            "Study Report Export 실패: "
            + ", ".join(
                errors
            )
        )


# =========================================================
# Azure Blob Storage Upload
# =========================================================

def _upload_study_outputs_to_blob() -> None:
    """
    생성된 Study Report 3개 파일을
    Azure Blob Storage의 reports 컨테이너에 업로드한다.

    실제 업로드 구현은 app.upload_reports_to_blob의 main()을
    재사용한다.

    import를 함수 안에서 수행해 Azure Blob SDK가 누락되어도
    백엔드 전체가 시작 단계에서 죽지 않도록 한다.
    """

    from app.upload_reports_to_blob import (
        main as upload_reports_to_blob,
    )

    upload_reports_to_blob()
