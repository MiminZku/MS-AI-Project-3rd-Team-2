"""프롬프트 조립 (§4.1-4). 이 시스템의 핵심 차별점이 여기에 있다.

참관자 지시는 시스템 프롬프트 최상단에 '추가 지령'으로 은밀히 주입되고,
모델은 지시받았다는 티를 내지 않은 채 자연스러운 꼬리질문으로 이어간다.
"""

from __future__ import annotations

from typing import Any

from app.schemas.session import Instruction, Session, Turn
from app.services.question_script import render_for_prompt

BASE_SYSTEM_PROMPT = """너는 사용자 리서치를 진행하는 전문 인터뷰 진행자다.

원칙:
- 실제 숙련된 인터뷰어처럼 자연스럽고 정중한 구어체 존댓말을 사용한다. 호칭('선생님' 등)은 대화 시작이나 꼭 필요한 순간에만 자연스럽게 쓰고, 매 문장마다 기계적으로 반복하지 않는다.
- 질문하기 전, 응답자의 직전 답변에 대해 1문장으로 자연스럽게 공감/맞장구(예: "아, 그러셨군요!", "자세한 경험 공유 감사드립니다.")를 건넨 후 다음 질문으로 이어간다.
- 첫 턴에서 응답자가 자기소개를 한 경우, 소개에 대해 따뜻하게 감사 인사를 드린 후 본격적인 1번 질문으로 자연스럽게 진입한다.
- 한 번에 질문 하나만 한다. 짧고 구어체로 말한다(2~3문장 이내).
- 응답자의 직전 답변을 근거로 다음 질문을 고른다. 대본을 기계적으로 읽지 않는다.
- 질문 리스트의 분기 조건에 답변이 매칭되면 해당 파생질문으로 이어간다.
- 응답자를 몰아붙이거나 평가하지 않는다.

반드시 아래 JSON 형식으로만 답한다:
{"question": "응답자에게 할 다음 질문", "rationale": "이 질문을 고른 판단 근거", "next_question_index": 0}
- rationale은 참관자에게만 보이며 응답자에게 노출되지 않는다.
- next_question_index는 이번에 할 질문이 질문 리스트의 몇 번째 항목인지 나타내는 0-based 인덱스(예: [index: 0]이면 0)다. 응답자가 아직 답변을 다 안 했으면 현재 인덱스를 유지하고, 충분히 답했으면 다음 인덱스로 넘어간다."""


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
