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
    taken_branches: list[str] | None = None,
    remaining_minutes: float | None = None,
    main_question_asked: bool = True,
) -> str:
    """프롬프트에 넣을 질문 트리 컨텍스트. 완료된 질문과 현재 질문, 예정 질문을 명확히 분리한다."""
    if not nodes:
        return "(질문 리스트가 비어 있음 — 주제에 맞춰 자유롭게 진행)"

    completed_set = set(completed_indices or [])
    taken_branch_set = set(taken_branches or [])
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

        # 3-a. 이번 메인 질문을 아직 한 번도 묻지 않은 상태.
        # 이 구간에서 파생질문 목록의 "1개를 골라 질문하라"는 지침을 노출하면
        # 모델이 핵심(메인) 질문을 건너뛰고 파생질문부터 물어버린다.
        if not main_question_asked:
            lines.append("【★ 이번 턴에 반드시 할 일: 아래 메인 질문을 묻기 (아직 한 번도 묻지 않음)】")
            lines.append(f"▶ [index: {current_index}] {curr_node.order}. {curr_node.text}")
            lines.append(
                "   👉 행동 지침: 이 메인 질문은 아직 응답자에게 전달되지 않았다. 직전 발화를 10자 내외로 짧게 인지한 뒤, "
                "반드시 위 메인 질문을 이번 발화에서 물어라. 파생질문·심화질문·다음 질문을 먼저 묻는 것은 절대 금지다. "
                f"(`next_question_index: {current_index}`, `is_sufficient: false`, `selected_branch: null`)"
            )
            if curr_node.branches:
                lines.append("   [참고용 - 지금 묻지 말 것]: 아래 파생질문들은 위 메인 질문의 답변을 들은 '다음 턴'에 고를 후보다.")
                for condition, question in curr_node.branches.items():
                    lines.append(f"   · [갈래: {condition}] -> {question}")
            lines.append("")
            return _finish(lines, nodes, current_index)

        # 3-b. 메인 질문을 이미 물었고 답변을 받은 상태 -> 파생질문 탐색 또는 다음 메인 질문 전이
        probe_info = f" (파생 꼬리질문 {probe_count}회 진행 상태)" if probe_count > 0 else " (메인 질문 답변 수신 상태)"
        lines.append("【★ 이번 턴에 진행할 질문 (이 질문만 다룰 것)】")
        lines.append(f"▶ [index: {current_index}] {curr_node.order}. {curr_node.text}{probe_info}")

        has_untaken_branch = False
        if curr_node.branches:
            lines.append("   [등록된 파생질문(Branch) 상태 목록]:")
            for condition, question in curr_node.branches.items():
                is_taken = condition in taken_branch_set or question in taken_branch_set
                if is_taken:
                    lines.append(f"   ✓ [이미 질문 완료됨 - 재질문 절대 금지]: [갈래: {condition}] -> {question}")
                else:
                    lines.append(f"   ▶ [미진행 파생질문]: [갈래: {condition}] -> {question}")
                    has_untaken_branch = True

        if has_untaken_branch and probe_count == 0:
            lines.append("   👉 행동 지침: 응답자 답변에 해당하는 [미진행 파생질문] 1개를 선택하여 질문하고, selected_branch에 해당 갈래명을 기입하세요 (is_sufficient: false).")
        else:
            # 파생질문이 없는 메인 질문도 여기로 들어온다. 예전에는 이 경우 아무 지침도
            # 렌더링되지 않아 모델이 같은 질문을 맴돌았다.
            next_index = current_index + 1
            if next_index < len(nodes):
                next_node = nodes[next_index]
                lines.append(
                    "   👉 행동 지침: 이 질문은 답변을 받았습니다. 같은 질문/예시를 다시 묻지 말고, 이번 발화에서 곧바로 "
                    f"다음 메인 질문 [index: {next_index}] \"{next_node.text}\" 를 물으세요 "
                    f"(`next_question_index: {next_index}`, `is_sufficient: true`, `selected_branch: null`)."
                )
            else:
                lines.append(
                    "   👉 행동 지침: 이 질문이 대본의 마지막 질문이며 답변까지 받았습니다. 마무리 및 감사 멘트를 하세요 "
                    f"(`next_question_index: {len(nodes)}`, `is_sufficient: true`, `selected_branch: null`)."
                )
        lines.append("")
    else:
        lines.append("【★ 모든 질문 완료】")
        # 대본은 끝났지만 예정 시간이 아직 넉넉히 남은 경우, 곧바로 종료하지 말고
        # 이미 확보한 사실(covered_facts) 중 하나를 골라 자연스럽게 더 깊이 파고든다.
        # (응답자가 "아직 시간 남았는데요"라고 이의를 제기해도 같은 종료 멘트만 반복하던 문제의 해결책)
        if remaining_minutes is not None and remaining_minutes > 2 and covered_facts:
            lines.append(
                f"▶ [index: {len(nodes)}] 대본 질문은 모두 마쳤지만 예정 시간이 아직 {remaining_minutes:.0f}분 남았습니다. "
                "곧바로 종료 멘트를 하지 마세요."
            )
            lines.append(
                "   👉 행동 지침: 아래 【이미 확보된 핵심 정보】 중 응답자가 흥미를 보였거나 좀 더 구체적으로 들을 만한 주제를 "
                "1개 골라 자연스러운 심화 질문을 하세요 (예: \"아까 말씀하신 ~에 대해 조금 더 자세히 들려주실 수 있을까요?\"). "
                "새로운 사실을 얻지 못했거나 응답자가 더 할 말이 없다고 하면 그때 종료 멘트를 하세요 "
                "(`next_question_index`는 계속 대본 총 개수를 유지, `is_sufficient: true`)."
            )
        else:
            lines.append(f"▶ [index: {len(nodes)}] 대본의 모든 질문을 마쳤습니다. 인터뷰 종료 및 감사 멘트를 하세요.")
        lines.append("")

    return _finish(lines, nodes, current_index)


def _finish(lines: list[str], nodes: list[QuestionNode], current_index: int) -> str:
    """공통 꼬리말: 이후 예정된 질문 목록을 붙이고 문자열로 만든다."""
    upcoming = [(i, node) for i, node in enumerate(nodes) if i > current_index]
    if upcoming:
        lines.append("【이후 예정된 질문】")
        for i, node in upcoming:
            lines.append(f"- [index: {i}] {node.order}. {node.text}")

    return "\n".join(lines)
