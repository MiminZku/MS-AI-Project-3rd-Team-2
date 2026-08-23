"""질문 트리 텍스트 파서 (§4.2).

입력 포맷:
    1. 배달앱을 얼마나 자주 쓰시나요?
    2. 최소주문금액에 대해 어떻게 느끼시나요?
       [부담됨] → 그 때문에 주문을 포기한 경험이 있나요?
       [보통]   → 최소주문금액을 맞추려고 더 시킨 적은 있나요?

파싱 결과는 (a) 대시보드 트리 UI, (b) GPT 프롬프트 컨텍스트 양쪽에 쓰인다.
"""

from __future__ import annotations

import re

from app.schemas.session import QuestionNode

_MAIN_RE = re.compile(r"^\s*(\d+)\s*[.)]\s*(.+?)\s*$")
_BRANCH_RE = re.compile(r"^\s*\[(?P<condition>[^\]]+)\]\s*(?:→|->)\s*(?P<question>.+?)\s*$")


def parse_question_script(script: str) -> list[QuestionNode]:
    nodes: list[QuestionNode] = []

    for raw_line in script.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue

        branch = _BRANCH_RE.match(line)
        if branch and nodes:
            condition = branch.group("condition").strip()
            nodes[-1].branches[condition] = branch.group("question").strip()
            continue

        main = _MAIN_RE.match(line)
        if main:
            order = int(main.group(1))
            nodes.append(QuestionNode(id=f"q{order}", order=order, text=main.group(2)))
            continue

        # 번호도 분기도 아닌 줄: 직전 질문의 이어쓰기로 취급
        if nodes:
            nodes[-1].text = f"{nodes[-1].text} {line.strip()}"

    return nodes


def render_for_prompt(nodes: list[QuestionNode], current_index: int) -> str:
    """프롬프트에 넣을 질문 트리 컨텍스트. 현재 위치를 표시한다."""
    if not nodes:
        return "(질문 리스트가 비어 있음 — 주제에 맞춰 자유롭게 진행)"

    lines: list[str] = []
    for i, node in enumerate(nodes):
        marker = " <== 현재 진행 중" if i == current_index else ""
        lines.append(f"[index: {i}] {node.order}. {node.text}{marker}")
        for condition, question in node.branches.items():
            lines.append(f"   [{condition}] -> {question}")
    return "\n".join(lines)
