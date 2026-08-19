import asyncio
import json

from app.api.routes.studies import create_study
from app.schemas.session import Instruction, Session, Turn
from app.schemas.study import ResearchStudyCreateRequest
from app.services.report.generator import generate


def build_question_script(session: Session) -> str:
    """
    dummy_interview.json의 질문을
    실제 ResearchStudy 생성에 사용할 질문지 문자열로 변환한다.

    질문 내용은 테스트 JSON에서 읽어오므로
    특정 질문이 코드에 하드코딩되지 않는다.
    """

    lines: list[str] = []

    for question in session.questions:

        # 메인 질문
        lines.append(
            f"{question.order}. {question.text}"
        )

        # 질문에 branch / probing 질문이 있으면
        # Slot Generator가 참고할 수 있도록 함께 전달
        for label, branch_text in question.branches.items():
            lines.append(
                f"   - {label}: {branch_text}"
            )

    return "\n".join(lines)


async def main():

    # =====================================================
    # 1. 기존 더미 인터뷰 읽기
    # =====================================================

    with open(
        "app/ai-interview-report/dummy_interview.json",
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    # =====================================================
    # 2. 기존 Session / Transcript / Instruction 복원
    # =====================================================

    original_session = Session.model_validate(
        data["session"]
    )

    transcript = [
        Turn.model_validate(turn)
        for turn in data["transcript"]
    ]

    instructions = [
        Instruction.model_validate(instruction)
        for instruction
        in data.get(
            "instructions",
            [],
        )
    ]

    # =====================================================
    # 3. 더미 질문을 ResearchStudy용 질문지로 변환
    #
    # 특정 질문을 test_report.py 안에 직접 작성하지 않는다.
    # dummy_interview.json의 질문이 바뀌면
    # 여기서 사용되는 질문도 자동으로 바뀐다.
    # =====================================================

    question_script = build_question_script(
        original_session
    )

    # =====================================================
    # 4. 실제 Study 생성 API 로직 실행
    #
    # create_study() 내부에서:
    #
    # 질문지 파싱
    # → GPT-5.1 Slot Generator
    # → Information Slot 자동 생성
    # → ResearchStudy 생성
    # → Store 저장
    #
    # 이 과정이 실제 서비스와 동일하게 실행된다.
    # =====================================================

    study_request = ResearchStudyCreateRequest(
        title=original_session.title,

        research_purpose=(
            "개발자가 AI 기반 코딩 도구를 선택하고 "
            "사용하는 과정에서 어떤 경험과 요인이 "
            "선호, 불편, 지속 사용 또는 전환 고려에 "
            "영향을 주는지 파악하고 제품 개선 기회를 "
            "도출한다."
        ),

        question_script=question_script,
    )

    study_response = await create_study(
        study_request
    )

    study = study_response.study

    # =====================================================
    # 5. 기존 인터뷰 Session을 방금 생성한 Study와 연결
    # =====================================================

    session = original_session.model_copy(
        update={
            "study_id": study.id,
        }
    )

    # =====================================================
    # 6. 생성된 Study 확인용 JSON 저장
    #
    # 실제로 어떤 Slot이 자동 생성됐는지
    # 눈으로 확인하기 위한 테스트 파일
    # =====================================================

    with open(
        "app/ai-interview-report/generated_study.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            study.model_dump(
                mode="json"
            ),
            file,
            ensure_ascii=False,
            indent=2,
        )

    # =====================================================
    # 7. 실제 Report Generator 실행
    #
    # generator.py:
    #
    # session.study_id
    # → Store에서 ResearchStudy 조회
    # → study.information_slots
    # → analyzer.py에 전달
    # → Slot Coverage 생성
    # =====================================================

    report = await generate(
        session=session,
        transcript=transcript,
        instructions=instructions,
    )

    # =====================================================
    # 8. 최종 리포트 저장
    # =====================================================

    with open(
        "app/ai-interview-report/participant_report.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report.model_dump(
                mode="json"
            ),
            file,
            ensure_ascii=False,
            indent=2,
        )

    # =====================================================
    # 9. 결과 출력
    # =====================================================

    print()
    print("========================================")
    print("ResearchStudy + Report 테스트 완료")
    print("========================================")

    print(
        "Study ID:",
        study.id,
    )

    print(
        "Session ID:",
        report.session_id,
    )

    print(
        "질문 수:",
        len(study.questions),
    )

    print(
        "자동 생성 Slot 수:",
        len(study.information_slots),
    )

    print()
    print("자동 생성된 Slot:")

    for slot in study.information_slots:
        print(
            f"- {slot.slot_id}"
            f" / {slot.question_id}"
            f" / {slot.slot_name}"
        )

    print()
    print(
        "generated_study.json 생성 완료"
    )

    print(
        "participant_report.json 생성 완료"
    )


asyncio.run(main())