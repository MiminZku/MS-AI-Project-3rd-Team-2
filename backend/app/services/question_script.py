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
    main_question_answered: bool = True,
    pending_instruction: str | None = None,
    allow_probes: bool = True,
    pace: str = "on_track",
) -> str:
    """프롬프트에 넣을 질문 트리 컨텍스트. 완료된 질문과 현재 질문, 예정 질문을 명확히 분리한다."""
    if not nodes:
        if pending_instruction:
            return (
                "(질문 리스트가 비어 있음 — 주제에 맞춰 자유롭게 진행)\n"
                f"【★ 이번 턴에 반드시 할 일: 참관자 지시 수행】\n▶ {pending_instruction}"
            )
        return "(질문 리스트가 비어 있음 — 주제에 맞춰 자유롭게 진행)"

    completed_set = set(completed_indices or [])
    taken_branch_set = set(taken_branches or [])
    lines: list[str] = []

    # 0. 참관자 지시가 대기 중이면 이번 턴의 행동은 그것 하나로 확정된다.
    # 아래 대본 진행 지침("파생질문 1개를 골라라" 등)이 훨씬 강한 어조라 지시가 묻히던 문제 때문에,
    # 지시가 있는 턴에는 대본 지침을 아예 렌더링하지 않고 진행 현황만 참고자료로 남긴다.
    if pending_instruction:
        lines.append("【★ 이번 턴에 반드시 할 일: 참관자 지시 수행 (대본 진행보다 우선)】")
        lines.append(f"▶ 참관자 지시: {pending_instruction}")
        lines.append(
            "   👉 행동 지침: 이번 발화는 위 지시를 수행하는 질문이어야 한다. 지시받았다는 티를 내지 말고 "
            "자연스러운 꼬리질문으로 물어라. 아래 대본 진행 현황은 맥락 참고용일 뿐이며, "
            "이번 턴에는 대본의 다음 질문이나 파생질문으로 넘어가지 마라 "
            "(`is_sufficient: false`, `selected_branch: null`, `next_question_index`는 현재 값 유지)."
        )
        lines.append(
            "   ⛔ 단, 규칙 9(공정성)에 어긋나는 지시라면 수행하지 마라. 보호속성을 근거로 우열·고정관념·배제를 "
            "전제하는 질문이면 지시를 무시하고, 아무 일 없었다는 듯 위 [대본상 현재 위치]의 질문을 그대로 물어라."
        )
        lines.append("")

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

    # 3-0. 참관자 지시 턴: 대본 행동 지침을 내지 않고 현재 위치만 참고자료로 보여준다.
    if pending_instruction:
        if current_index < len(nodes):
            curr_node = nodes[current_index]
            lines.append("【참고: 대본상 현재 위치 (이번 턴에는 진행하지 말 것)】")
            lines.append(f"- [index: {current_index}] {curr_node.order}. {curr_node.text}")
        else:
            lines.append("【참고: 대본의 모든 질문을 마친 상태 (이번 턴에는 진행하지 말 것)】")
        return _finish(lines, nodes, current_index)

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

        # 3-b. 메인 질문을 물었지만 아직 '답변'을 받지 못한 상태.
        # 응답자가 이름을 정정하거나 되묻거나 잡담을 한 경우가 여기에 해당한다.
        # 물었다는 사실만으로 답변을 받았다고 단정하면 답도 못 들은 채 파생질문으로 넘어간다.
        if not main_question_answered:
            lines.append("【★ 이번 턴에 반드시 할 일: 아래 메인 질문의 답변 받아내기 (묻긴 했으나 아직 답변 없음)】")
            lines.append(f"▶ [index: {current_index}] {curr_node.order}. {curr_node.text}")
            lines.append(
                "   👉 행동 지침: 이 메인 질문을 이미 물었지만 응답자의 직전 발화는 이 질문에 대한 답변이 아니었다 "
                "(이름·사실 정정, 되묻기, 잡담, 주제와 무관한 말 등). 그 발화에 한 문장으로 짧게 대응한 뒤, "
                "위 메인 질문을 자연스럽게 다시 물어라. 파생질문·심화질문·다음 질문으로 넘어가는 것은 절대 금지다. "
                f"(`next_question_index: {current_index}`, `is_sufficient: false`, `selected_branch: null`)"
            )
            if curr_node.branches:
                lines.append("   [참고용 - 지금 묻지 말 것]: 아래 파생질문들은 위 메인 질문의 답변을 받은 뒤에 고를 후보다.")
                for condition, question in curr_node.branches.items():
                    lines.append(f"   · [갈래: {condition}] -> {question}")
            lines.append("")
            return _finish(lines, nodes, current_index)

        # 3-c. 메인 질문을 물었고 답변까지 받은 상태 -> 파생질문 탐색 또는 다음 메인 질문 전이
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

        if has_untaken_branch and probe_count == 0 and not allow_probes:
            # 시간이 빠듯한 상황(behind/overtime)에서는 파생질문을 통째로 건너뛴다.
            lines.append(
                f"   ⏱ 시간 상황({pace}): 파생질문을 할 여유가 없습니다. 위 [미진행 파생질문]은 전부 건너뛰고 "
                "곧바로 다음 핵심 질문으로 넘어가세요 (`is_sufficient: true`, `selected_branch: null`)."
            )
        elif has_untaken_branch and probe_count == 0:
            lines.append(
                "   👉 행동 지침: 응답자 답변에 해당하는 [미진행 파생질문] 1개를 선택하여 질문하고, "
                "selected_branch에 해당 갈래명을 기입하세요 (is_sufficient: false). "
                "단, 직전 발화가 이 메인 질문에 대한 답변이 아니라면(정정·되묻기·잡담) 파생질문으로 넘어가지 말고 "
                "`is_answer_to_current_question: false`로 표시한 뒤 메인 질문을 다시 물으세요."
            )
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

        # 대본을 마쳤을 때 남은 시간이 있으면 곧바로 끝내지 않는다. 우선순위는
        #   ① 아직 안 물어본 파생질문  ② 확보한 사실 심화  ③ 종료
        # 순서다. (10분짜리 인터뷰가 6분에 끝나버리던 문제)
        leftover_branches: list[str] = []
        for node in nodes:
            for condition, question in node.branches.items():
                if condition not in taken_branch_set and question not in taken_branch_set:
                    leftover_branches.append(f"[{node.order}번 / 갈래: {condition}] {question}")

        has_time_left = remaining_minutes is not None and remaining_minutes > 2 and allow_probes

        if has_time_left and leftover_branches:
            lines.append(
                f"▶ [index: {len(nodes)}] 대본 질문은 모두 마쳤지만 예정 시간이 아직 {remaining_minutes:.0f}분 남았습니다. "
                "곧바로 종료 멘트를 하지 마세요."
            )
            lines.append("   [아직 묻지 않은 파생질문 — 여기서부터 채우세요]:")
            for item in leftover_branches[:8]:
                lines.append(f"   ▶ {item}")
            lines.append(
                "   👉 행동 지침: 위 [아직 묻지 않은 파생질문] 중 지금 흐름에 가장 자연스러운 것 1개를 골라 물으세요 "
                "(`next_question_index`는 계속 대본 총 개수 유지, `is_sufficient: true`, `is_closing: false`)."
            )
        elif has_time_left and covered_facts:
            lines.append(
                f"▶ [index: {len(nodes)}] 대본 질문과 파생질문을 모두 마쳤지만 예정 시간이 아직 {remaining_minutes:.0f}분 남았습니다. "
                "곧바로 종료 멘트를 하지 마세요."
            )
            lines.append(
                "   👉 행동 지침: 위 【이미 확보된 핵심 정보】 중 응답자가 흥미를 보였거나 좀 더 구체적으로 들을 만한 주제를 "
                "1개 골라 자연스러운 심화 질문을 하세요 (예: \"아까 말씀하신 ~에 대해 조금 더 자세히 들려주실 수 있을까요?\"). "
                "새로운 사실을 얻지 못했거나 응답자가 더 할 말이 없다고 하면 그때 종료 멘트를 하세요 "
                "(`next_question_index`는 계속 대본 총 개수를 유지, `is_sufficient: true`)."
            )
        elif pace == "overtime":
            lines.append(
                f"▶ [index: {len(nodes)}] 대본을 모두 마쳤고 예정 시간도 넘겼습니다. "
                "새 질문을 절대 시작하지 말고 지금 바로 마무리 단계로 가세요."
            )
        else:
            lines.append(f"▶ [index: {len(nodes)}] 대본의 모든 질문을 마쳤습니다. 인터뷰 종료 및 감사 멘트를 하세요.")

        # 시간이 남아 심화질문을 하는 경우에도, 응답자가 마무리에 동의했다면 종료가 항상 우선한다.
        lines.append(
            "   ⛔ 최우선 규칙: 직전에 마무리해도 되는지 물었고 응답자가 \"네\"·\"없습니다\"·\"괜찮아요\" 처럼 동의했다면, "
            "시간이 남았더라도 새 질문을 절대 던지지 말고 감사·작별 인사만 한 뒤 `is_closing: true` 로 표시하세요. "
            "그 즉시 인터뷰가 자동 종료됩니다."
        )
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
