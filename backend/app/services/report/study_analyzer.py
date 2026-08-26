from __future__ import annotations

import json
import os
import re
from typing import Any

from dotenv import load_dotenv
from openai import AsyncAzureOpenAI

from app.services.report.structured_call import create_structured_json

from app.core.config import get_settings
from app.schemas.study import ResearchStudy
from app.schemas.study_report import (
    StudyEvidenceReference,
    StudyReportAnalysis,
)

load_dotenv()


class StudyReportAnalyzer:
    """
    여러 명의 개별 인터뷰 분석 결과를 받아 Study 단위 종합 리포트를 생성한다.

    원칙
    - 특정 조사 주제, 제품, 참여자 수, 질문 수에 종속되지 않는다.
    - Study마다 조사 목적 / 질문 / Information Slot이 달라질 수 있다.
    - 최종 리포트 상위 구조만 고정한다.
    - Evidence 원본은 AI가 다시 생성하지 않는다.
    - 개별 리포트마다 E001부터 다시 시작할 수 있으므로
      Study 분석 전에 participant namespace를 붙여 Evidence ID를 유일하게 만든다.
    """

    def __init__(self) -> None:
        settings = get_settings()
        endpoint = settings.azure_openai_endpoint
        api_key = settings.azure_openai_api_key
        deployment = settings.azure_openai_chat_deployment
        api_version = settings.azure_openai_api_version

        if not endpoint:
            raise RuntimeError(
                "AZURE_OPENAI_ENDPOINT가 설정되지 않았습니다."
            )

        if not api_key:
            raise RuntimeError(
                "AZURE_OPENAI_API_KEY가 설정되지 않았습니다."
            )

        self.deployment = deployment

        self.client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )

    # 검증 실패시 재시도 횟수. 모델이 evidence_ids를 빈 배열로 남기는 등
    # 스키마로는 못 잡는 비즈니스 규칙 위반은 가끔씩 일어난다. 재시도 없이
    # 바로 실패시키면 참여자가 3명뿐인 작은 Study에서도 리포트 생성이
    # 자주 실패해서 사용자가 매번 재클릭해야 했다.
    MAX_VALIDATION_RETRIES = 2

    # 시도별 temperature. 첫 시도는 결정적으로(0) 뽑되, 재시도는 온도를 올려
    # 실제로 다른 출력이 나오게 한다. 온도를 0으로 고정한 채 재시도하면
    # 거의 같은 답이 다시 나와서 재시도가 무의미해진다.
    RETRY_TEMPERATURES = (0.0, 0.4, 0.7)

    async def analyze(
        self,
        study: ResearchStudy,
        participant_reports: list[
            dict[str, Any]
        ],
    ) -> StudyReportAnalysis:

        if not participant_reports:
            raise ValueError(
                "종합 분석할 participant_reports가 없습니다."
            )

        normalized_reports = (
            self._normalize_participant_reports(
                participant_reports
            )
        )

        last_error: ValueError | None = None

        for attempt in range(self.MAX_VALIDATION_RETRIES + 1):
            try:
                return await self._generate_once(
                    study=study,
                    normalized_reports=normalized_reports,
                    retry_feedback=(
                        str(last_error) if last_error else None
                    ),
                    temperature=self.RETRY_TEMPERATURES[
                        min(attempt, len(self.RETRY_TEMPERATURES) - 1)
                    ],
                )
            except ValueError as error:
                # ValueError는 모델 출력이 비즈니스 규칙(예: evidence 누락)을
                # 어긴 경우다. 재시도할수록 무슨 문제였는지 프롬프트에 알려주면
                # 모델이 스스로 고칠 확률이 높다. JSON 파싱 실패나 네트워크
                # 오류(RuntimeError 등)는 재시도해도 같은 결과일 가능성이 커서
                # 여기서 잡지 않고 그대로 올린다.
                last_error = error
                if attempt >= self.MAX_VALIDATION_RETRIES:
                    raise

        # 위 for 루프는 항상 return 또는 raise로 끝난다.
        raise AssertionError("unreachable")

    async def _generate_once(
        self,
        *,
        study: ResearchStudy,
        normalized_reports: list[dict[str, Any]],
        retry_feedback: str | None,
        temperature: float = 0.0,
    ) -> StudyReportAnalysis:

        input_payload = {
            "study": {
                "study_id": study.id,
                "title": study.title,
                "research_purpose": (
                    study.research_purpose
                ),
                "question_script": (
                    study.question_script
                ),
                "questions": [
                    question.model_dump(
                        mode="json"
                    )
                    for question
                    in study.questions
                ],
                "information_slots": [
                    slot.model_dump(
                        mode="json"
                    )
                    for slot
                    in study.information_slots
                ],
            },

            "participant_count": len(
                normalized_reports
            ),

            "participant_reports": (
                normalized_reports
            ),

            "important_output_rule": (
                "최종 evidence 필드는 반드시 "
                "빈 배열 []로 반환한다. "
                "Evidence Library는 서버가 원본 "
                "인터뷰 데이터에서 직접 복원한다. "
                "다른 분석 항목의 evidence_ids에는 "
                "입력에 실제 존재하는 evidence_id만 "
                "정확히 사용한다."
            ),
        }

        if retry_feedback:
            # 직전 시도가 어떤 규칙을 어겼는지 그대로 알려준다. 예:
            # "executive_summary.key_takeaways[1]: Evidence가 없습니다."
            # -> 모델이 그 항목만 빼거나 근거를 채워 다시 시도하게 유도한다.
            input_payload["previous_attempt_validation_error"] = (
                "직전 시도한 결과가 다음 이유로 거부되었습니다. "
                "같은 문제가 다시 발생하지 않도록 주의해서 다시 생성하세요: "
                f"{retry_feedback}"
            )

        content = (
            await create_structured_json(
                self.client,
                deployment=self.deployment,

                system_prompt=(
                    self._build_system_prompt()
                ),

                user_input=json.dumps(
                    input_payload,
                    ensure_ascii=False,
                ),

                schema_name=(
                    "study_report_analysis"
                ),

                schema=(
                    StudyReportAnalysis
                    .model_json_schema()
                ),

                max_output_tokens=20000,

                temperature=temperature,
            )
        )

        if not content:
            raise RuntimeError(
                "Study 종합 분석 결과가 비어 있습니다."
            )

        try:
            raw_result = json.loads(
                content
            )

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Study 종합 분석 결과를 "
                "JSON으로 읽을 수 없습니다."
            ) from exc

        result = (
            StudyReportAnalysis
            .model_validate(
                raw_result
            )
        )

        result = (
            self._replace_overview(
                result=result,
                study=study,
                participant_reports=(
                    normalized_reports
                ),
            )
        )

        result = (
            self._replace_evidence_library(
                result=result,
                participant_reports=(
                    normalized_reports
                ),
            )
        )

        result = (
            self._sanitize_segment_differences(
                result=result,
                participant_reports=(
                    normalized_reports
                ),
            )
        )

        self._validate_result(
            result=result,
            participant_reports=(
                normalized_reports
            ),
            study=study,
        )

        return result

    def _normalize_participant_reports(
        self,
        participant_reports: list[
            dict[str, Any]
        ],
    ) -> list[dict[str, Any]]:
        """
        개별 리포트를 Study 분석 입력 구조로 정규화한다.

        개별 Report의 Evidence ID는 참여자마다
        E001, E002처럼 다시 시작할 수 있다.

        Study 단위에서는 충돌하지 않도록:

            P01 + E001 -> P01_E001
            P02 + E001 -> P02_E001

        로 바꾼다.

        Evidence 본체뿐 아니라 report 내부의 모든
        evidence_id / evidence_ids 참조를
        같은 규칙으로 함께 바꾼다.
        """

        normalized: list[
            dict[str, Any]
        ] = []

        used_participant_ids: set[
            str
        ] = set()

        for index, report in enumerate(
            participant_reports,
            start=1,
        ):

            if not isinstance(
                report,
                dict,
            ):
                raise ValueError(
                    f"participant_reports[{index}]가 "
                    "dict 형식이 아닙니다."
                )

            data = report.get(
                "data",
                report,
            )

            if not isinstance(
                data,
                dict,
            ):
                raise ValueError(
                    "participant report data가 "
                    "dict 형식이 아닙니다. "
                    f"index={index}"
                )

            participant_id = (
                report.get(
                    "participant_id"
                )
                or data.get(
                    "participant_id"
                )
                or f"P{index:02d}"
            )

            participant_id = str(
                participant_id
            ).strip()

            if not participant_id:
                participant_id = (
                    f"P{index:02d}"
                )

            if (
                participant_id
                in used_participant_ids
            ):
                raise ValueError(
                    "중복된 participant_id가 있습니다: "
                    f"{participant_id}"
                )

            used_participant_ids.add(
                participant_id
            )

            session_id = (
                report.get(
                    "session_id"
                )
                or report.get(
                    "id"
                )
                or data.get(
                    "session_id"
                )
                or (
                    f"unknown_session_"
                    f"{index}"
                )
            )

            raw_evidence = data.get(
                "evidence",
                [],
            )

            if not isinstance(
                raw_evidence,
                list,
            ):
                raise ValueError(
                    "participant report의 evidence가 "
                    "list 형식이 아닙니다. "
                    f"participant_id={participant_id}"
                )

            prefix = (
                f"{participant_id}_"
            )

            evidence_id_map: dict[
                str,
                str,
            ] = {}

            for evidence in (
                raw_evidence
            ):

                if not isinstance(
                    evidence,
                    dict,
                ):
                    continue

                raw_id = evidence.get(
                    "evidence_id"
                )

                if not isinstance(
                    raw_id,
                    str,
                ):
                    continue

                old_id = (
                    raw_id.strip()
                )

                if not old_id:
                    continue

                if old_id.startswith(
                    prefix
                ):
                    new_id = old_id

                else:
                    new_id = (
                        f"{participant_id}_"
                        f"{old_id}"
                    )

                evidence_id_map[
                    old_id
                ] = new_id

            def rewrite_evidence_references(
                value: Any,
            ) -> Any:

                if isinstance(
                    value,
                    dict,
                ):

                    rewritten: dict[
                        str,
                        Any,
                    ] = {}

                    for key, item in (
                        value.items()
                    ):

                        if (
                            key
                            == "evidence_id"
                            and isinstance(
                                item,
                                str,
                            )
                        ):

                            lookup = (
                                item.strip()
                            )

                            rewritten[
                                key
                            ] = (
                                evidence_id_map
                                .get(
                                    lookup,
                                    item,
                                )
                            )

                            continue

                        if (
                            key
                            == "evidence_ids"
                            and isinstance(
                                item,
                                list,
                            )
                        ):

                            rewritten[
                                key
                            ] = [
                                (
                                    evidence_id_map
                                    .get(
                                        evidence_id
                                        .strip(),
                                        evidence_id,
                                    )
                                )
                                if isinstance(
                                    evidence_id,
                                    str,
                                )
                                else evidence_id
                                for evidence_id
                                in item
                            ]

                            continue

                        rewritten[
                            key
                        ] = (
                            rewrite_evidence_references(
                                item
                            )
                        )

                    return rewritten

                if isinstance(
                    value,
                    list,
                ):

                    return [
                        rewrite_evidence_references(
                            item
                        )
                        for item in value
                    ]

                return value

            namespaced_data = (
                rewrite_evidence_references(
                    data
                )
            )

            if not isinstance(
                namespaced_data,
                dict,
            ):
                raise ValueError(
                    "Evidence namespace 처리 후 "
                    "report data가 dict 형식이 아닙니다. "
                    f"participant_id={participant_id}"
                )

            normalized.append(
                {
                    "participant_id": (
                        participant_id
                    ),

                    "session_id": (
                        str(
                            session_id
                        )
                    ),

                    "participant_context": (
                        namespaced_data
                        .get(
                            "participant_context",
                            {},
                        )
                    ),

                    "executive_summary": (
                        namespaced_data
                        .get(
                            "executive_summary",
                            {},
                        )
                    ),

                    "research_coverage": (
                        namespaced_data
                        .get(
                            "research_coverage",
                            {},
                        )
                    ),

                    "slot_coverage": (
                        namespaced_data
                        .get(
                            "slot_coverage",
                            {},
                        )
                    ),

                    "key_findings": (
                        namespaced_data
                        .get(
                            "key_findings",
                            [],
                        )
                    ),

                    "themes": (
                        namespaced_data
                        .get(
                            "themes",
                            [],
                        )
                    ),

                    "key_drivers": (
                        namespaced_data
                        .get(
                            "key_drivers",
                            [],
                        )
                    ),

                    "needs_and_pain_points": (
                        namespaced_data
                        .get(
                            "needs_and_pain_points",
                            [],
                        )
                    ),

                    "decision_dynamics": (
                        namespaced_data
                        .get(
                            "decision_dynamics"
                        )
                    ),

                    "opportunities": (
                        namespaced_data
                        .get(
                            "opportunities",
                            [],
                        )
                    ),

                    "researcher_attention": (
                        namespaced_data
                        .get(
                            "researcher_attention",
                            [],
                        )
                    ),

                    "evidence": (
                        namespaced_data
                        .get(
                            "evidence",
                            [],
                        )
                    ),
                }
            )

        return normalized

    def _build_system_prompt(
        self,
    ) -> str:

        return """
당신은 여러 건의 정성 인터뷰를 종합 분석하는
Senior UX Researcher / Market Research Analyst입니다.

이 시스템은 특정 제품, 산업, 조사 주제에 종속되지 않습니다.

Research Study마다 다음 항목은 달라질 수 있습니다.

- 조사 목적
- 조사 주제
- 질문 내용
- 질문 개수
- Information Slot
- 참여자 수
- 참여자 특성

따라서 특정 제품명,
특정 참여자 수,
특정 질문 개수를 전제로 분석하면 안 됩니다.

최종 Study Report의 상위 구조만 고정하고,
실제 내용과 항목 수는 현재 Study 데이터에 맞춰
동적으로 생성하세요.


=========================================================
핵심 출력
=========================================================

- Executive Summary
- Research Coverage
- Cross-Interview Key Findings
- Themes
- Key Drivers
- Pain Points
- Needs
- Segment Differences
- Opportunities
- Research Gaps

모든 주요 분석은
실제 interviewee Evidence에 근거해야 합니다.


=========================================================
Evidence 원칙
=========================================================

1.
실제 참여자 발화 quote가
최종 근거입니다.

2.
개별 리포트의 AI 요약문 자체를
새로운 Evidence처럼 사용하지 마세요.

3.
evidence_id는 입력 participant_reports에
존재하는 값을 문자 하나까지
정확히 그대로 사용하세요.

4.
존재하지 않는 Evidence ID를 만들지 마세요.

5.
Evidence ID 형식을 임의로 수정하지 마세요.

6.
최종 JSON의 evidence 필드는
반드시 빈 배열 []로 반환하세요.

전체 Evidence Library는
서버가 원본 participant_reports에서
결정적으로 복원합니다.

7.
다음 섹션의 evidence_ids에는
실제 입력 Evidence ID만 연결하세요.

- executive_summary.key_takeaways
- key_findings
- themes
- key_drivers
- pain_points
- needs
- segment_differences
- opportunities

8.
각 Evidence가 해당 분석 내용을
직접 지지하는지 확인하세요.

9. [매우 중요]
위 7번 목록에 속한 항목은
evidence_ids를 절대 빈 배열로 남기면 안 됩니다.
각 항목마다 반드시 1개 이상의
실제 Evidence ID를 연결하세요.

특정 항목에 직접 인용할 발화가
마땅치 않다면, 그 항목을 아예 작성하지 말고
목록에서 제외하세요.
evidence_ids가 비어 있는 항목을 포함해서는
안 됩니다.


=========================================================
Participant 원칙
=========================================================

participant_count는
해당 분석 내용을 실제로 지지하는
고유 참여자의 수입니다.

반드시:

participant_count
==
len(participant_ids)

여야 합니다.

같은 참여자가 같은 내용을
여러 번 말해도 한 명으로 계산합니다.

participant_ids에는
실제 입력에 존재하는 참여자만 사용하세요.

participant_ids에 포함된 모든 참여자는
해당 분석을 직접 지지하는 Evidence를
최소 하나 가져야 합니다.


=========================================================
정성조사 해석 원칙
=========================================================

현재 Study 표본을
시장 전체나 사용자 전체로
일반화하지 마세요.

금지 예:

"사용자의 대부분은..."
"개발자의 70%는..."
"전체 시장에서는..."
"일반적으로 사용자들은..."

허용 예:

"본 Study 참여자 중..."
"이번 인터뷰 표본에서는..."
"여러 참여자에게서..."
"해당 패턴은 N명에게서 확인됐다."

현재 표본의 count는 표현할 수 있지만
시장 비율처럼 표현하면 안 됩니다.


=========================================================
미래 행동 / 전환 / 구매 / 이탈
=========================================================

미래 행동은 매우 보수적으로 해석하세요.

다음과 같은 직접 Evidence가 있어야 합니다.

"이 기능이 생기면 다시 사용하겠습니다."
"가격이 더 싸지면 구매를 고려할 겁니다."
"이 문제가 계속되면 다른 도구로 바꿀 겁니다."

단순 불편,
선호,
기능 희망만으로
미래 행동을 추론하지 마세요.


=========================================================
Research Coverage
=========================================================

단순히 질문을 했다는 이유만으로
coverage를 high로 평가하지 마세요.

조사 목적에 필요한 정보를
실제로 얼마나 확보했는지를 봅니다.

high:
여러 참여자의 이유, 조건, 사례 등이
충분히 확보된 경우

medium:
유의미한 정보는 있으나
구체 사례나 조건이 일부 부족한 경우

low:
단편적인 정보만 있는 경우

not_covered:
실질적으로 필요한 정보를
거의 확보하지 못한 경우

participant_count:
전체 Study 참여자 수

covered_participant_count:
해당 질문에 의미 있는 정보를 제공한
참여자 수

participant_ids:
실제로 해당 질문을
유의미하게 커버한 참여자


=========================================================
Cross-Interview Key Findings
=========================================================

개별 인터뷰 Finding을
그대로 복사하지 마세요.

여러 인터뷰를 비교해
Study 차원의 패턴을 만드세요.

가능하면 최소 2명 이상의
독립 참여자에게서 확인되는 패턴을
Finding으로 사용하세요.

한 명에게서만 나온 중요한 신호는
필요하다면:

- Need
- Opportunity
- Research Gap

등에 제한적으로 배치하세요.


=========================================================
Themes
=========================================================

Theme은 Finding보다
한 단계 상위의 개념적 패턴이어야 합니다.

Finding을 단순히
다른 말로 반복하지 마세요.

여러 Finding 또는
여러 참여자의 경험을 관통하는
개념이어야 합니다.


=========================================================
Key Drivers
=========================================================

Driver는 단순 불만이 아니라
실제로 참여자의:

- 현재 선택
- 평가
- 사용 방식
- 현재 행동

에 영향을 준 요인이어야 합니다.

직접 Evidence 없이
미래 행동을 추론하지 마세요.


=========================================================
Pain Points
=========================================================

Pain Point는
실제 경험에서 나타난 문제입니다.

같은 근본 원인의 문제는
하나의 상위 Pain Point로
통합할 수 있습니다.

서로 다른 문제를
억지로 묶지 마세요.


=========================================================
Needs
=========================================================

Need는 Pain Point 문장을
단순히 긍정형으로 바꾼 것이 아닙니다.

실제 사용자가 필요로 하는:

- 상태
- 능력
- 해결 방향

이어야 합니다.

가능하면 Pain Point와 연결되는
사용자 요구가 명확해야 합니다.


=========================================================
Segment Differences
=========================================================

Segment 분석은
매우 보수적으로 생성하세요.

하나의 Segment Difference에는
최소 2개의 비교 그룹이 필요합니다.

각 그룹에는 최소 2명의
고유 참여자가 있어야 합니다.

따라서:

1명 vs 1명
금지

3명 vs 1명
금지

2명 vs 2명
가능

4명 vs 3명
가능

같은 참여자가
서로 다른 그룹에 동시에
들어가면 안 됩니다.

각 group의 participant_count는
participant_ids 개수와 같아야 합니다.

각 그룹의 모든 참여자는
그 그룹 특성을 직접 지지하는
Evidence를 최소 하나 가져야 합니다.

Segment 전체 participant_ids는
각 그룹 participant_ids의
합집합이어야 합니다.

Segment 전체 evidence_ids는
각 group evidence_ids를
모두 포함해야 합니다.

표본이 부족하다면
segment_differences를
빈 배열로 반환해도 됩니다.


=========================================================
Opportunity source_type
=========================================================

source_type은:

explicit_user_request
derived_opportunity

두 종류입니다.


---------------------------------------------------------
explicit_user_request
---------------------------------------------------------

참여자가 핵심 기능 또는
해결 방향 자체를
직접 말한 경우입니다.

예:

"배송이 늦어지면
미리 알림을 보내줬으면 좋겠어요."

이 경우:

explicit_user_request


---------------------------------------------------------
derived_opportunity
---------------------------------------------------------

참여자는 문제만 말했고
분석자가 새로운 해결책을
도출한 경우입니다.

예:

참여자:
"배송이 언제 오는지 몰라
계속 조회해야 했습니다."

분석자:
"예측 ETA 기반 자동 알림"

참여자가 그 기능을 직접
말하지 않았다면:

derived_opportunity

분석자가 만든 아이디어를
사용자의 직접 요구처럼
표현하지 마세요.


=========================================================
Opportunities
=========================================================

유사한 Opportunity는
통합하세요.

한 참여자에게서만 나온
직접 요청도
의미가 있다면 포함할 수 있습니다.

하지만 한 사람의 요구를
"사용자들의 공통 요구"
라고 과장하면 안 됩니다.

expected_value에는
확정적인 사업 효과를
말하지 마세요.

금지:

"사용률이 증가한다."
"이탈률이 감소한다."
"매출이 오른다."
"시장 점유율이 증가한다."

허용:

"마찰을 줄일 가능성이 있다."
"사용 경험 개선의 여지가 있다."
"추가 검증이 필요하다."


=========================================================
Research Gaps
=========================================================

이번 Study에서
아직 충분히 답하지 못했지만
추가 조사 가치가 높은 내용을 적으세요.

예:

- 한 명에게서만 나온 신호
- Segment로 보기에는 표본이 부족한 차이
- 검증되지 않은 인과관계
- 제품 아이디어의 실제 행동 효과
- 추가 비교가 필요한 조건


=========================================================
최종 Self Check
=========================================================

최종 JSON 출력 전에 확인하세요.

1.
participant_count와
participant_ids 개수가 일치하는가?

2.
존재하지 않는 participant_id를
만들지 않았는가?

3.
Evidence ID는
입력에 존재하는 정확한 ID인가?

4.
존재하지 않는 evidence_id를
만들지 않았는가?

5.
각 Evidence가
해당 분석 내용을 직접 지지하는가?

6.
한 참여자의 의견을
다수 의견처럼 표현하지 않았는가?

7.
현재 Study 결과를
시장 전체로 일반화하지 않았는가?

8.
행동 / 전환 / 구매 / 이탈을
직접 Evidence 없이 추론하지 않았는가?

9.
explicit_user_request와
derived_opportunity를
정확하게 구분했는가?

10.
Segment의 각 비교 그룹에
최소 2명의 참여자가 있는가?

11.
서로 다른 Segment 그룹에
같은 사람이 포함되지 않았는가?

12.
관련 없는 Evidence를
같은 참여자의 발언이라는 이유만으로
연결하지 않았는가?

13.
최종 evidence 필드는
반드시 빈 배열 []인가?
"""

    def _get_expected_question_count(
        self,
        study: ResearchStudy,
    ) -> int:

        if study.questions:
            return len(
                study.questions
            )

        pattern = re.compile(
            r"^\s*\d+\s*[.)]\s*.+$"
        )

        return sum(
            1
            for line
            in (
                study.question_script
                .splitlines()
            )
            if pattern.match(
                line
            )
        )

    def _replace_overview(
        self,
        result: StudyReportAnalysis,
        study: ResearchStudy,
        participant_reports: list[
            dict[str, Any]
        ],
    ) -> StudyReportAnalysis:

        overview = (
            result.overview.model_copy(
                update={
                    "study_id": (
                        study.id
                    ),

                    "research_title": (
                        study.title
                    ),

                    "research_purpose": (
                        study.research_purpose
                    ),

                    "participant_count": (
                        len(
                            participant_reports
                        )
                    ),

                    "completed_session_count": (
                        len(
                            participant_reports
                        )
                    ),

                    "question_count": (
                        self
                        ._get_expected_question_count(
                            study
                        )
                    ),
                }
            )
        )

        return result.model_copy(
            update={
                "overview": (
                    overview
                ),
            }
        )

    def _build_evidence_owner(
        self,
        participant_reports: list[
            dict[str, Any]
        ],
    ) -> dict[str, str]:

        evidence_owner: dict[
            str,
            str,
        ] = {}

        for report in (
            participant_reports
        ):

            participant_id = (
                report[
                    "participant_id"
                ]
            )

            for evidence in (
                report.get(
                    "evidence",
                    [],
                )
            ):

                evidence_id = (
                    evidence.get(
                        "evidence_id"
                    )
                )

                if not evidence_id:
                    continue

                if (
                    evidence_id
                    in evidence_owner
                ):
                    raise ValueError(
                        "입력 Evidence에 "
                        "중복된 evidence_id가 있습니다: "
                        f"{evidence_id}"
                    )

                evidence_owner[
                    evidence_id
                ] = participant_id

        return evidence_owner

    def _replace_evidence_library(
        self,
        result: StudyReportAnalysis,
        participant_reports: list[
            dict[str, Any]
        ],
    ) -> StudyReportAnalysis:

        source_evidence: list[
            StudyEvidenceReference
        ] = []

        seen_evidence_ids: set[
            str
        ] = set()

        for report in (
            participant_reports
        ):

            participant_id = (
                report[
                    "participant_id"
                ]
            )

            session_id = (
                report[
                    "session_id"
                ]
            )

            for evidence in (
                report.get(
                    "evidence",
                    [],
                )
            ):

                evidence_id = (
                    evidence.get(
                        "evidence_id"
                    )
                )

                if not evidence_id:
                    continue

                if (
                    evidence_id
                    in seen_evidence_ids
                ):
                    raise ValueError(
                        "입력 Evidence에 "
                        "중복된 evidence_id가 있습니다: "
                        f"{evidence_id}"
                    )

                seen_evidence_ids.add(
                    evidence_id
                )

                source_evidence.append(
                    StudyEvidenceReference(
                        evidence_id=(
                            evidence_id
                        ),

                        participant_id=(
                            participant_id
                        ),

                        session_id=(
                            session_id
                        ),

                        quote=(
                            evidence.get(
                                "quote",
                                "",
                            )
                        ),

                        question_id=(
                            evidence.get(
                                "question_id"
                            )
                        ),
                    )
                )

        return result.model_copy(
            update={
                "evidence": (
                    source_evidence
                ),
            }
        )

    def _sanitize_segment_differences(
        self,
        result: StudyReportAnalysis,
        participant_reports: list[
            dict[str, Any]
        ],
    ) -> StudyReportAnalysis:

        valid_participant_ids = {
            report[
                "participant_id"
            ]
            for report
            in participant_reports
        }

        evidence_owner = (
            self._build_evidence_owner(
                participant_reports
            )
        )

        valid_evidence_ids = set(
            evidence_owner.keys()
        )

        cleaned_segments = []

        for segment in (
            result.segment_differences
        ):

            if len(
                segment.groups
            ) < 2:
                continue

            segment_is_valid = True

            group_names: set[
                str
            ] = set()

            all_group_participants: set[
                str
            ] = set()

            all_group_evidence: list[
                str
            ] = []

            for group in (
                segment.groups
            ):

                normalized_group_name = (
                    group.group_name
                    .strip()
                    .lower()
                )

                if not normalized_group_name:
                    segment_is_valid = False
                    break

                if (
                    normalized_group_name
                    in group_names
                ):
                    segment_is_valid = False
                    break

                group_names.add(
                    normalized_group_name
                )

                participant_ids = (
                    group.participant_ids
                )

                unique_participants = set(
                    participant_ids
                )

                if (
                    len(
                        unique_participants
                    )
                    != len(
                        participant_ids
                    )
                ):
                    segment_is_valid = False
                    break

                if (
                    len(
                        unique_participants
                    )
                    < 2
                ):
                    segment_is_valid = False
                    break

                if (
                    group.participant_count
                    != len(
                        participant_ids
                    )
                ):
                    segment_is_valid = False
                    break

                if not (
                    unique_participants
                    <= valid_participant_ids
                ):
                    segment_is_valid = False
                    break

                if (
                    all_group_participants
                    & unique_participants
                ):
                    segment_is_valid = False
                    break

                evidence_ids = (
                    group.evidence_ids
                )

                if not evidence_ids:
                    segment_is_valid = False
                    break

                if (
                    len(
                        evidence_ids
                    )
                    != len(
                        set(
                            evidence_ids
                        )
                    )
                ):
                    segment_is_valid = False
                    break

                if not (
                    set(
                        evidence_ids
                    )
                    <= valid_evidence_ids
                ):
                    segment_is_valid = False
                    break

                evidence_participants = {
                    evidence_owner[
                        evidence_id
                    ]
                    for evidence_id
                    in evidence_ids
                }

                if not (
                    evidence_participants
                    <= unique_participants
                ):
                    segment_is_valid = False
                    break

                if not (
                    unique_participants
                    <= evidence_participants
                ):
                    segment_is_valid = False
                    break

                all_group_participants.update(
                    unique_participants
                )

                for evidence_id in (
                    evidence_ids
                ):

                    if (
                        evidence_id
                        not in
                        all_group_evidence
                    ):
                        all_group_evidence.append(
                            evidence_id
                        )

            if not segment_is_valid:
                continue

            if (
                len(
                    all_group_participants
                )
                < 4
            ):
                continue

            ordered_participant_ids: list[
                str
            ] = []

            for group in (
                segment.groups
            ):

                for participant_id in (
                    group.participant_ids
                ):

                    if (
                        participant_id
                        not in
                        ordered_participant_ids
                    ):
                        ordered_participant_ids.append(
                            participant_id
                        )

            cleaned_segment = (
                segment.model_copy(
                    update={
                        "participant_count": (
                            len(
                                ordered_participant_ids
                            )
                        ),

                        "participant_ids": (
                            ordered_participant_ids
                        ),

                        "evidence_ids": (
                            all_group_evidence
                        ),
                    }
                )
            )

            cleaned_segments.append(
                cleaned_segment
            )

        return result.model_copy(
            update={
                "segment_differences": (
                    cleaned_segments
                ),
            }
        )

    def _validate_result(
        self,
        result: StudyReportAnalysis,
        participant_reports: list[
            dict[str, Any]
        ],
        study: ResearchStudy,
    ) -> None:

        valid_participant_ids = {
            report[
                "participant_id"
            ]
            for report
            in participant_reports
        }

        evidence_owner = (
            self._build_evidence_owner(
                participant_reports
            )
        )

        valid_evidence_ids = set(
            evidence_owner.keys()
        )

        expected_participant_count = (
            len(
                participant_reports
            )
        )

        if (
            result
            .overview
            .participant_count
            != expected_participant_count
        ):
            raise ValueError(
                "overview.participant_count가 "
                "실제 참여자 수와 다릅니다. "
                f"expected="
                f"{expected_participant_count}, "
                f"actual="
                f"{result.overview.participant_count}"
            )

        if (
            result
            .overview
            .completed_session_count
            != expected_participant_count
        ):
            raise ValueError(
                "overview.completed_session_count가 "
                "실제 완료 세션 수와 다릅니다."
            )

        expected_question_count = (
            self._get_expected_question_count(
                study
            )
        )

        if (
            result
            .overview
            .question_count
            != expected_question_count
        ):
            raise ValueError(
                "overview.question_count가 "
                "Study 질문 수와 다릅니다. "
                f"expected="
                f"{expected_question_count}, "
                f"actual="
                f"{result.overview.question_count}"
            )

        def validate_item(
            participant_count: int,
            participant_ids: list[
                str
            ],
            evidence_ids: list[
                str
            ],
            section_name: str,
            minimum_participants: int = 1,
        ) -> None:

            unique_participants = set(
                participant_ids
            )

            if (
                len(
                    unique_participants
                )
                != len(
                    participant_ids
                )
            ):
                raise ValueError(
                    f"{section_name}: "
                    "participant_ids에 "
                    "중복이 있습니다."
                )

            if (
                participant_count
                != len(
                    participant_ids
                )
            ):
                raise ValueError(
                    f"{section_name}: "
                    "participant_count와 "
                    "participant_ids 수가 다릅니다."
                )

            if (
                participant_count
                < minimum_participants
            ):
                raise ValueError(
                    f"{section_name}: "
                    f"최소 "
                    f"{minimum_participants}명의 "
                    "참여자가 필요합니다."
                )

            invalid_participants = (
                unique_participants
                - valid_participant_ids
            )

            if invalid_participants:
                raise ValueError(
                    f"{section_name}: "
                    "존재하지 않는 "
                    "participant_id가 있습니다: "
                    f"{sorted(invalid_participants)}"
                )

            if not evidence_ids:
                raise ValueError(
                    f"{section_name}: "
                    "Evidence가 없습니다."
                )

            if (
                len(
                    evidence_ids
                )
                != len(
                    set(
                        evidence_ids
                    )
                )
            ):
                raise ValueError(
                    f"{section_name}: "
                    "evidence_ids에 "
                    "중복이 있습니다."
                )

            invalid_evidence = (
                set(
                    evidence_ids
                )
                - valid_evidence_ids
            )

            if invalid_evidence:
                raise ValueError(
                    f"{section_name}: "
                    "존재하지 않는 "
                    "evidence_id가 있습니다: "
                    f"{sorted(invalid_evidence)}"
                )

            evidence_participants = {
                evidence_owner[
                    evidence_id
                ]
                for evidence_id
                in evidence_ids
            }

            unrelated_participants = (
                evidence_participants
                - unique_participants
            )

            if unrelated_participants:
                raise ValueError(
                    f"{section_name}: "
                    "participant_ids에 없는 "
                    "참여자의 Evidence가 "
                    "연결되어 있습니다: "
                    f"{sorted(unrelated_participants)}"
                )

            participants_without_evidence = (
                unique_participants
                - evidence_participants
            )

            if (
                participants_without_evidence
            ):
                raise ValueError(
                    f"{section_name}: "
                    "직접 Evidence가 없는 "
                    "참여자가 포함되었습니다: "
                    f"{sorted(participants_without_evidence)}"
                )

        for index, item in enumerate(
            result
            .executive_summary
            .key_takeaways,
            start=1,
        ):

            validate_item(
                participant_count=(
                    item.participant_count
                ),

                participant_ids=(
                    item.participant_ids
                ),

                evidence_ids=(
                    item.evidence_ids
                ),

                section_name=(
                    "executive_summary."
                    f"key_takeaways[{index}]"
                ),
            )

        for index, item in enumerate(
            result
            .research_coverage
            .items,
            start=1,
        ):

            if (
                item.participant_count
                != expected_participant_count
            ):
                raise ValueError(
                    "research_coverage."
                    f"items[{index}]: "
                    "participant_count는 "
                    "Study 전체 참여자 수와 "
                    "같아야 합니다."
                )

            if (
                item
                .covered_participant_count
                != len(
                    item.participant_ids
                )
            ):
                raise ValueError(
                    "research_coverage."
                    f"items[{index}]: "
                    "covered_participant_count와 "
                    "participant_ids 수가 "
                    "다릅니다."
                )

            if (
                len(
                    item.participant_ids
                )
                != len(
                    set(
                        item.participant_ids
                    )
                )
            ):
                raise ValueError(
                    "research_coverage."
                    f"items[{index}]: "
                    "participant_ids에 "
                    "중복이 있습니다."
                )

            invalid_ids = (
                set(
                    item.participant_ids
                )
                - valid_participant_ids
            )

            if invalid_ids:
                raise ValueError(
                    "research_coverage."
                    f"items[{index}]: "
                    "존재하지 않는 "
                    "participant_id가 있습니다: "
                    f"{sorted(invalid_ids)}"
                )

            if (
                item
                .covered_participant_count
                > expected_participant_count
            ):
                raise ValueError(
                    "research_coverage."
                    f"items[{index}]: "
                    "covered_participant_count가 "
                    "전체 참여자 수보다 큽니다."
                )

        for item in (
            result.key_findings
        ):

            validate_item(
                participant_count=(
                    item.participant_count
                ),

                participant_ids=(
                    item.participant_ids
                ),

                evidence_ids=(
                    item.evidence_ids
                ),

                section_name=(
                    "key_findings."
                    f"{item.finding_id}"
                ),

                minimum_participants=2,
            )

        for item in (
            result.themes
        ):

            validate_item(
                participant_count=(
                    item.participant_count
                ),

                participant_ids=(
                    item.participant_ids
                ),

                evidence_ids=(
                    item.evidence_ids
                ),

                section_name=(
                    "themes."
                    f"{item.theme_id}"
                ),

                minimum_participants=2,
            )

        for item in (
            result.key_drivers
        ):

            validate_item(
                participant_count=(
                    item.participant_count
                ),

                participant_ids=(
                    item.participant_ids
                ),

                evidence_ids=(
                    item.evidence_ids
                ),

                section_name=(
                    "key_drivers."
                    f"{item.driver_id}"
                ),
            )

        for item in (
            result.pain_points
        ):

            validate_item(
                participant_count=(
                    item.participant_count
                ),

                participant_ids=(
                    item.participant_ids
                ),

                evidence_ids=(
                    item.evidence_ids
                ),

                section_name=(
                    "pain_points."
                    f"{item.pain_point_id}"
                ),
            )

        for item in (
            result.needs
        ):

            validate_item(
                participant_count=(
                    item.participant_count
                ),

                participant_ids=(
                    item.participant_ids
                ),

                evidence_ids=(
                    item.evidence_ids
                ),

                section_name=(
                    "needs."
                    f"{item.need_id}"
                ),
            )

        for (
            segment_index,
            segment,
        ) in enumerate(
            result.segment_differences,
            start=1,
        ):

            if (
                len(
                    segment.groups
                )
                < 2
            ):
                raise ValueError(
                    "segment_differences"
                    f"[{segment_index}]: "
                    "최소 2개의 비교 그룹이 "
                    "필요합니다."
                )

            all_group_participants: set[
                str
            ] = set()

            all_group_evidence: set[
                str
            ] = set()

            for (
                group_index,
                group,
            ) in enumerate(
                segment.groups,
                start=1,
            ):

                validate_item(
                    participant_count=(
                        group.participant_count
                    ),

                    participant_ids=(
                        group.participant_ids
                    ),

                    evidence_ids=(
                        group.evidence_ids
                    ),

                    section_name=(
                        "segment_differences"
                        f"[{segment_index}]"
                        ".groups"
                        f"[{group_index}]"
                    ),

                    minimum_participants=2,
                )

                current_group_ids = set(
                    group.participant_ids
                )

                overlap = (
                    all_group_participants
                    & current_group_ids
                )

                if overlap:
                    raise ValueError(
                        "segment_differences"
                        f"[{segment_index}]: "
                        "서로 다른 그룹에 "
                        "동일 참여자가 있습니다: "
                        f"{sorted(overlap)}"
                    )

                all_group_participants.update(
                    current_group_ids
                )

                all_group_evidence.update(
                    group.evidence_ids
                )

            if (
                len(
                    all_group_participants
                )
                < 4
            ):
                raise ValueError(
                    "segment_differences"
                    f"[{segment_index}]: "
                    "전체 Segment에는 "
                    "최소 4명의 참여자가 필요합니다."
                )

            if (
                set(
                    segment.participant_ids
                )
                != all_group_participants
            ):
                raise ValueError(
                    "segment_differences"
                    f"[{segment_index}]: "
                    "Segment participant_ids와 "
                    "groups 참여자 합집합이 "
                    "다릅니다."
                )

            if (
                segment.participant_count
                != len(
                    all_group_participants
                )
            ):
                raise ValueError(
                    "segment_differences"
                    f"[{segment_index}]: "
                    "participant_count가 "
                    "실제 그룹 참여자 수와 "
                    "다릅니다."
                )

            if (
                set(
                    segment.evidence_ids
                )
                != all_group_evidence
            ):
                raise ValueError(
                    "segment_differences"
                    f"[{segment_index}]: "
                    "Segment evidence_ids와 "
                    "groups Evidence 합집합이 "
                    "다릅니다."
                )

        for item in (
            result.opportunities
        ):

            validate_item(
                participant_count=(
                    item.participant_count
                ),

                participant_ids=(
                    item.participant_ids
                ),

                evidence_ids=(
                    item.evidence_ids
                ),

                section_name=(
                    "opportunities."
                    f"{item.opportunity_id}"
                ),
            )

        seen_evidence_ids: set[
            str
        ] = set()

        for item in (
            result.evidence
        ):

            if (
                item.participant_id
                not in valid_participant_ids
            ):
                raise ValueError(
                    "Study Evidence에 "
                    "존재하지 않는 "
                    "participant_id가 있습니다: "
                    f"{item.participant_id}"
                )

            if (
                item.evidence_id
                not in valid_evidence_ids
            ):
                raise ValueError(
                    "Study Evidence에 "
                    "존재하지 않는 "
                    "evidence_id가 있습니다: "
                    f"{item.evidence_id}"
                )

            expected_owner = (
                evidence_owner[
                    item.evidence_id
                ]
            )

            if (
                item.participant_id
                != expected_owner
            ):
                raise ValueError(
                    "Study Evidence의 "
                    "participant_id와 "
                    "실제 Evidence 소유자가 "
                    "다릅니다. "
                    f"evidence_id="
                    f"{item.evidence_id}, "
                    f"expected="
                    f"{expected_owner}, "
                    f"actual="
                    f"{item.participant_id}"
                )

            if (
                item.evidence_id
                in seen_evidence_ids
            ):
                raise ValueError(
                    "Study Evidence Library에 "
                    "중복 evidence_id가 있습니다: "
                    f"{item.evidence_id}"
                )

            seen_evidence_ids.add(
                item.evidence_id
            )

        if (
            seen_evidence_ids
            != valid_evidence_ids
        ):

            missing = (
                valid_evidence_ids
                - seen_evidence_ids
            )

            extra = (
                seen_evidence_ids
                - valid_evidence_ids
            )

            raise ValueError(
                "Study Evidence Library와 "
                "원본 Evidence가 "
                "일치하지 않습니다. "
                f"missing="
                f"{sorted(missing)}, "
                f"extra="
                f"{sorted(extra)}"
            )


# =========================================================
# Singleton
# =========================================================

_study_report_analyzer: (
    StudyReportAnalyzer | None
) = None


def get_study_report_analyzer(
) -> StudyReportAnalyzer:

    global _study_report_analyzer

    if (
        _study_report_analyzer
        is None
    ):
        _study_report_analyzer = (
            StudyReportAnalyzer()
        )

    return _study_report_analyzer