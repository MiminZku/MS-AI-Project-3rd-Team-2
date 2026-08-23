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
5. [대본 완주]: 응답자의 답변에 맞추어 대본의 모든 핵심 질문을 누락 없이 순차적으로 충실하게 소화한다.

반드시 아래 JSON 형식으로만 답한다:
{"question": "응답자에게 할 다음 질문 (인지 1구절 + 다음 질문 1구절)", "rationale": "이 질문을 선택한 논리적 근거", "next_question_index": 0}
- rationale은 참관자(백룸)에게만 보이며 응답자에게 노출되지 않는다.
- next_question_index는 이번 질문이 속한 메인 질문의 0-based 인덱스다."""


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

    if timekeeper_hint:
        messages.append({"role": "system", "content": f"(진행 상황 참고: {timekeeper_hint})"})

    for turn in transcript:
        role = "user" if turn.speaker == "interviewee" else "assistant"
        messages.append({"role": role, "content": turn.text})

    return messages
