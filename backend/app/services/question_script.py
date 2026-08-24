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


def render_for_prompt(
    nodes: list[QuestionNode],
    current_index: int,
    completed_indices: list[int] | None = None,
    probe_count: int = 0,
    covered_facts: dict[str, str] | None = None,
) -> str:
    """프롬프트에 넣을 질문 트리 컨텍스트. 완료된 질문과 현재 질문, 예정 질문을 명확히 분리한다."""
    if not nodes:
        return "(질문 리스트가 비어 있음 — 주제에 맞춰 자유롭게 진행)"

    completed_set = set(completed_indices or [])
    lines: list[str] = []

    # 1. 이미 획득한 핵심 사실
    if covered_facts:
        lines.append("【이미 확보된 핵심 정보 (절대 다시 묻지 말 것)】")
        for k, v in covered_facts.items():
            lines.append(f"- {k}: {v}")
        lines.append("")

    # 2. 이미 완료된 질문들
    completed_nodes = [node for i, node in enumerate(nodes) if i in completed_set or i < current_index]
    if completed_nodes:
        lines.append("【이미 완료된 질문 (다시 묻거나 언급 금지)】")
        for node in completed_nodes:
            lines.append(f"✓ [완료] {node.order}. {node.text}")
        lines.append("")

    # 3. 현재 진행 대상 질문 (단 1개)
    if current_index < len(nodes):
        curr_node = nodes[current_index]
        probe_info = f" (현재 질문 꼬리질문 {probe_count}회차 진행 중)" if probe_count > 0 else ""
        lines.append("【★ 이번 턴에 진행할 질문 (이 질문만 다룰 것)】")
        lines.append(f"▶ [index: {current_index}] {curr_node.order}. {curr_node.text}{probe_info}")
        if curr_node.branches:
            for condition, question in curr_node.branches.items():
                lines.append(f"   [조건: {condition}] -> {question}")
        lines.append("")
    else:
        lines.append("【★ 모든 질문 완료】")
        lines.append(f"▶ [index: {len(nodes)}] 대본의 모든 질문을 마쳤습니다. 인터뷰 종료 및 감사 멘트를 하세요.")
        lines.append("")

    # 4. 이후 예정된 질문들
    upcoming_nodes = [node for i, node in enumerate(nodes) if i > current_index]
    if upcoming_nodes:
        lines.append("【이후 예정된 질문】")
        for i, node in enumerate(nodes):
            if i > current_index:
                lines.append(f"- [index: {i}] {node.order}. {node.text}")

    return "\n".join(lines)
