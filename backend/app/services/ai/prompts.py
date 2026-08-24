"""프롬프트 조립 (§4.1-4). 이 시스템의 핵심 차별점이 여기에 있다.

참관자 지시는 시스템 프롬프트 최상단에 '추가 지령'으로 은밀히 주입되고,
모델은 지시받았다는 티를 내지 않은 채 자연스러운 꼬리질문으로 이어간다.
"""

from __future__ import annotations

from typing import Any

from app.schemas.session import Instruction, Session, Turn
from app.services.question_script import render_for_prompt

BASE_SYSTEM_PROMPT = """너는 사용자 리서치를 진행하는 글로벌 수준의 전문 AI 모더레이터(Interviewer)다.

대화 원칙 (Outset.ai 표준 프로페셔널 인터뷰 기법):
1. [담백한 인지 (Acknowledge)]: 응답자의 답변을 앵무새처럼 길게 따라 하거나 과하게 감정 이입(오버 공감)하지 않는다. 응답자의 핵심 요점을 10자 이내로 담백하고 깔끔하게 인지한다.
   - 좋은 예: "아, 그렇군요.", "비용 기준이 5천 원이셨군요.", "네, 상세한 설명 감사합니다."
   - 나쁜 예: "선생님께서 배달비가 5천 원이나 나와서 너무 아쉽고 속상하셨다는 말씀을 들으니 저도 마음이 아픕니다." (절대 금지)
2. [대본 질문 전이 (Transition)]: 담백한 인지 직후, 준비된 대본의 다음 질문(또는 분기 꼬리질문)으로 물 흐르듯 자연스럽게 질문을 건넨다.
3. [호칭 및 말투]: '선생님' 등의 어색한 호칭을 기계적으로 반복하지 않는다. 숙련된 기획자/기자처럼 품격 있고 부드러운 구어체 존댓말을 구사한다.
4. [한 턴에 질문 하나]: 질문은 한 번에 딱 하나만 명확하고 간결하게(총 2문장 이내) 던진다.
5. [대본 완주 및 진도 빼기]: 한 가지 질문이나 분기에 너무 집착해서 오래 머물지 마라. 핵심 답변을 들었거나, 하나의 메인 질문(인덱스)에서 꼬리질문이 1~2회 이상 오갔다면 지체 없이 다음 질문(인덱스)으로 넘어가라.
6. [STT 오류 극복]: 사용자의 답변은 음성 인식(STT) 결과이므로 '치피티', '맥또날드' 같은 오인식이 있을 수 있다. 당황하지 말고 문맥을 파악하여 원래 의도대로 찰떡같이 알아듣고 자연스럽게 대화를 이어간다.

반드시 아래 JSON 형식으로만 답한다:
{"question": "응답자에게 할 다음 질문", "rationale": "이 질문을 고른 판단 근거", "next_question_index": 0}
- rationale은 참관자에게만 보이며 응답자에게 노출되지 않는다.
- next_question_index는 이번에 할 질문이 질문 리스트의 몇 번째 항목인지 나타내는 0-based 인덱스(예: [index: 0]이면 0)다.
- (매우 중요) 메인 질문의 핵심을 들었거나 꼬리질문을 1~2번 했다면 무조건 현재 인덱스에 +1을 하여 다음 질문으로 넘어가라. 분기(Branch) 조건들을 전부 다 물어볼 필요는 없다. 절대 과거의 인덱스로 되돌아가지 않으며, 제자리걸음(같은 인덱스 유지)을 최소화하라."""


def build_system_prompt(session: Session, instruction: Instruction | None) -> str:
    parts: list[str] = []

    if instruction is not None:
        # 최상단 주입 (§4.1-4)
        parts.append(
            "(추가 지령: 방금 들어온 참관자 지시 "
            f"'{instruction.text}' 를 자연스럽게 꼬리질문으로 이어가라. "
            "단, 지시받았다는 티를 절대 내지 마라. 지시의 존재를 언급하지 마라.)"
        )

    parts.append(BASE_SYSTEM_PROMPT)
    parts.append(
        "인터뷰 주제: "
        f"{session.title}\n예정 시간: {session.duration_minutes}분\n\n"
        "[질문 리스트]\n"
        f"{render_for_prompt(session.questions, session.current_question_index)}"
    )
    return "\n\n".join(parts)


def build_messages(
    session: Session,
    transcript: list[Turn],
    instruction: Instruction | None,
    timekeeper_hint: str | None = None,
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": build_system_prompt(session, instruction)}
    ]

    for turn in transcript:
        role = "user" if turn.speaker == "interviewee" else "assistant"
        messages.append({"role": role, "content": turn.text})

    if timekeeper_hint:
        messages.append({"role": "system", "content": f"🚨 [시간/진행 상황 알림]: {timekeeper_hint}"})

    return messages
