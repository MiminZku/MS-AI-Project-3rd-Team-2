from __future__ import annotations

import json
import logging
from typing import Any, Protocol

from app.core.config import get_settings
from app.schemas.report_analysis import (
    IndividualInterviewAnalysis,
)
from app.schemas.session import (
    Instruction,
    Session,
    Turn,
)
from app.schemas.study import ResearchStudy


logger = logging.getLogger(__name__)


# =========================================================
# Analyzer Interface
# =========================================================

class ReportAnalyzer(Protocol):

    async def analyze(
        self,
        session: Session,
        transcript: list[Turn],
        instructions: list[Instruction],
        study: ResearchStudy | None,
    ) -> dict[str, Any]:
        ...


# =========================================================
# Stub Analyzer
# =========================================================

class StubReportAnalyzer:

    async def analyze(
        self,
        session: Session,
        transcript: list[Turn],
        instructions: list[Instruction],
        study: ResearchStudy | None,
    ) -> dict[str, Any]:

        slots = (
            study.information_slots
            if study
            else []
        )

        return {
            "participant_context": {
                "summary": "[STUB]",
                "attributes": [],
            },

            "executive_summary": {
                "core_insight": "[STUB]",
                "summary": "[STUB]",
                "key_takeaways": [],
            },

            "research_coverage": {
                "overall_coverage": "low",
                "items": [],
            },

            "slot_coverage": {
                "overall_coverage": "low",
                "items": [
                    {
                        "slot_id": slot.slot_id,
                        "question_id": slot.question_id,
                        "slot_name": slot.slot_name,
                        "coverage": "not_covered",
                        "reason": "Azure OpenAI 미연결",
                        "evidence_ids": [],
                        "missing_information": [
                            slot.description
                        ],
                    }
                    for slot in slots
                ],
            },

            "key_findings": [],

            "themes": [],

            "key_drivers": [],

            "needs_and_pain_points": [],

            "decision_dynamics": None,

            "opportunities": [],

            "observer_intervention_analysis": [],

            "researcher_attention": [],

            "analysis_metadata": {
                "mode": "azure_openai",
            },
        }


# =========================================================
# Azure OpenAI Analyzer
# =========================================================

class AzureOpenAIReportAnalyzer:

    def __init__(self) -> None:
        from openai import AsyncAzureOpenAI

        settings = get_settings()

        self._deployment = (
            settings.azure_openai_chat_deployment
        )

        self._client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            timeout=120.0,
        )


    async def analyze(
        self,
        session: Session,
        transcript: list[Turn],
        instructions: list[Instruction],
        study: ResearchStudy | None,
    ) -> dict[str, Any]:

        # =================================================
        # 1. 실제 응답자 Evidence Library 생성
        # =================================================

        interviewee_turns = [
            turn
            for turn in transcript
            if turn.speaker == "interviewee"
        ]

        evidence_library: list[
            dict[str, Any]
        ] = []

        for number, turn in enumerate(
            interviewee_turns,
            start=1,
        ):
            evidence_library.append(
                {
                    "evidence_id": f"E{number:03d}",
                    "turn_index": turn.index,
                    "speaker": turn.speaker,
                    "quote": turn.text,
                    "created_at": (
                        turn.created_at.isoformat()
                    ),
                }
            )

        allowed_evidence_ids = {
            item["evidence_id"]
            for item in evidence_library
        }

        # =================================================
        # 2. 이번 Study에서 자동 생성된 Slot
        # =================================================

        required_slots: list[
            dict[str, Any]
        ] = []

        if study:
            required_slots = [
                slot.model_dump(
                    mode="json"
                )
                for slot
                in study.information_slots
            ]

        # =================================================
        # 3. GPT 입력 데이터
        # =================================================

        input_data = {
            "research": {
                "study_id": (
                    study.id
                    if study
                    else None
                ),

                "title": (
                    study.title
                    if study
                    else session.title
                ),

                "research_purpose": (
                    study.research_purpose
                    if study
                    else None
                ),
            },

            "session": {
                "session_id": session.id,
                "study_id": session.study_id,

                "duration_minutes": (
                    session.duration_minutes
                ),

                "started_at": (
                    session.started_at.isoformat()
                    if session.started_at
                    else None
                ),

                "ended_at": (
                    session.ended_at.isoformat()
                    if session.ended_at
                    else None
                ),
            },

            "questions": [
                question.model_dump(
                    mode="json"
                )
                for question
                in session.questions
            ],

            "required_slots": required_slots,

            "transcript": [
                turn.model_dump(
                    mode="json"
                )
                for turn
                in transcript
            ],

            "observer_instructions": [
                instruction.model_dump(
                    mode="json"
                )
                for instruction
                in instructions
            ],

            "evidence_library": (
                evidence_library
            ),
        }

        # =================================================
        # 4. 범용 정성 인터뷰 분석 Prompt
        # =================================================

        system_prompt = """
당신은 기업 시장조사 및 UX Research 전문
정성 인터뷰 분석가입니다.

한 명의 인터뷰 결과를 분석하여
Individual Interview Report를 작성합니다.

이 시스템에는 다양한 산업과 주제의
인터뷰가 들어올 수 있습니다.

특정 제품, 산업, 브랜드,
사용자 행동을 미리 가정하지 마세요.

반드시 이번 입력에 포함된

- research
- questions
- required_slots
- transcript
- evidence_library
- observer_instructions

만을 기준으로 분석하세요.


==================================================
[핵심 분석 원칙]
==================================================

리포트의 목적은
인터뷰 내용을 길게 반복하는 것이 아니라,

연구자가 짧은 시간 안에

1. 무엇을 알게 되었는지
2. 왜 중요한지
3. 어떤 근거가 있는지
4. 아직 무엇을 모르는지

이해할 수 있게 만드는 것입니다.

같은 내용을 여러 섹션에서
문장만 바꿔 반복하지 마세요.

각 섹션은 서로 다른 역할을 가져야 합니다.


==================================================
[Evidence 규칙]
==================================================

Evidence는 반드시
speaker가 interviewee인
실제 응답자의 발언만 사용합니다.

assistant의 질문에 포함된

- 주장
- 예시
- 가정
- 유도 문구

는 응답자의 Evidence가 아닙니다.

observer의 지시 또한
응답자의 Evidence가 아닙니다.

응답자가 실제로 말하지 않은 내용을
응답자의 의견처럼 작성하지 마세요.

모든 중요한 분석에는
Evidence Library에 실제 존재하는
evidence_id를 연결하세요.

존재하지 않는 evidence_id를
새로 만들지 마세요.


==================================================
[추론 강도]
==================================================

Evidence에서 직접 확인되는 사실과
분석자가 도출한 해석을 구분하세요.

응답자가 명확히 말한 내용보다
더 강한 표현을 사용하지 마세요.

예:

응답자:
"이 기능이 있으면 불편이 많이 줄 것 같다"

잘못된 해석:
"이 기능이 생기면 해당 제품으로 전환한다."

올바른 해석:
"이 기능은 현재 불편을 줄일 가능성이 있는
개선 요인으로 언급되었다."


==================================================
[숫자 / 비율 / 정량 표현 규칙]
==================================================

응답자가

"80%"
"절반"
"거의 대부분"
"8할"

등의 숫자나 비율을 말한 경우,

그 수치는 객관적인 제품 성과나
시장 수치가 아닙니다.

반드시

"응답자는 자신의 불편이 약 80% 줄 것이라고 기대했다"

처럼

'응답자 개인의 주관적 예상'

이라는 점을 명확하게 표현하세요.

다음처럼 쓰지 마세요:

"이 기능은 불편을 80% 감소시킨다."

"제품 만족도가 80% 향상될 것이다."

인터뷰 한 명의 발언을
제품 성과 예측으로 변환하지 마세요.


==================================================
[일반화 금지]
==================================================

현재 데이터는
한 명의 인터뷰 결과입니다.

한 명의 응답을 근거로

"사용자들은"
"고객들은"
"시장에서는"
"개발자들은"
"대부분은"

처럼 일반화하지 마세요.

대신

"이 응답자는"
"본 인터뷰에서는"
"이 참여자의 경험에서는"

처럼 표현하세요.


==================================================
[섹션 간 중복 방지]
==================================================

같은 내용을 여러 섹션에서
그대로 반복하지 마세요.

각 섹션의 목적은 다음과 같습니다.

Executive Summary:
가장 중요한 결론만 빠르게 전달.

Key Findings:
조사 목적과 직접 연결되는
구체적인 연구 발견.

Themes:
여러 Evidence를 관통하는
상위 패턴이나 공통 주제.

Key Drivers:
응답자의 판단이나 행동에
영향을 준 요인.

Needs and Pain Points:
응답자가 경험한 문제나 필요.

Opportunities:
앞의 Evidence와 문제를 바탕으로
실행 가능한 개선 기회.

같은 내용을 넣어야 하는 경우에도
각 섹션의 역할에 맞는
새로운 분석적 의미가 있어야 합니다.

단순 문장 재작성은 피하세요.


==================================================
[출력 개수 가이드]
==================================================

리포트가 지나치게 길어지지 않도록
핵심 항목만 선택하세요.

가능하면:

key_findings:
3~5개

themes:
2~4개

key_drivers:
2~4개

needs_and_pain_points:
핵심적인 항목만 2~5개

opportunities:
근거가 충분한 항목만 1~4개

researcher_attention:
가장 중요한 추가 확인 사항 2~5개

를 권장합니다.

Evidence가 부족하다면
최소 개수를 억지로 채우지 마세요.

빈 배열도 가능합니다.


==================================================
[Participant Context]
==================================================

participant_context에는
이번 인터뷰에서 실제로 확인된
응답자의 배경과 상황만 정리하세요.

특정 필드를 미리 가정하지 않습니다.

attributes의 name/value를 사용하여
이번 조사에 중요한 정보를 표현하세요.

예:

직무
경험 수준
현재 사용 방식
이용 빈도
역할
사용 제품
관련 경험

응답자가 말하지 않은
인구통계 정보나 경력을
추측하지 마세요.

각 attribute에는
근거 evidence_ids를 연결하세요.


==================================================
[Executive Summary]
==================================================

Executive Summary는
전체 리포트를 읽지 않아도
이번 인터뷰의 의미를 알 수 있게 작성합니다.

core_insight:
조사 목적 관점에서
가장 중요한 결론 하나.

summary:
핵심 흐름을 짧고 명확하게 설명.

key_takeaways:
연구자가 반드시 기억해야 하는
핵심 내용만 작성.

세부 사례를 모두 반복하지 마세요.

세부 사례는
Key Findings와 Evidence에서 다룹니다.


==================================================
[Question Coverage]
==================================================

research_coverage는
질문이 실제로 제시됐는지를
평가하는 것이 아닙니다.

해당 질문을 통해
연구자가 알고 싶었던 정보가
얼마나 확보됐는지 평가합니다.

coverage:

high
medium
low
not_covered


high:
연구 판단에 필요한 핵심 정보와
구체적인 근거가 충분히 확보됨.

medium:
핵심 답변은 있지만
사례, 이유, 조건 등의
세부 정보가 일부 부족함.

low:
관련 언급은 있지만
연구 판단에 사용하기 부족함.

not_covered:
실제 응답에서
해당 정보를 확인하지 못함.


질문에 답했다는 이유만으로
high를 주지 마세요.


==================================================
[Slot Coverage]
==================================================

required_slots는
이번 ResearchStudy의
조사 목적과 질문지를 기반으로
미리 생성된 Information Slot입니다.

required_slots가 존재하면
모든 Slot을 정확히 하나씩 평가하세요.

새 Slot을 만들지 마세요.

Slot을 삭제하거나
누락하지 마세요.

각 Slot에는 반드시:

slot_id
question_id
slot_name
coverage
reason
evidence_ids
missing_information

을 작성하세요.


coverage:

high
medium
low
not_covered


high:
해당 정보를 판단할 수 있을 정도로
명확하고 구체적인 Evidence가 있음.

medium:
핵심 정보는 있지만
이유, 사례, 조건, 범위 등이
일부 부족함.

low:
관련 언급만 존재하고
해당 Slot을 판단하기에는 부족함.

not_covered:
실제 응답에서
해당 정보를 확인할 수 없음.


중요:

importance와 coverage는
서로 다른 개념입니다.

importance:
연구에서 이 정보가 얼마나 중요한가.

coverage:
이번 인터뷰에서 실제로
얼마나 확보되었는가.

importance가 high라고 해서
coverage도 high가 아닙니다.

required_slots가 빈 배열이면
slot_coverage.items도
빈 배열로 반환하세요.


==================================================
[Key Findings]
==================================================

Key Finding은
단순 답변 요약이 아닙니다.

research_purpose와 직접 관련되어
연구자가 의사결정에 활용할 수 있는
발견만 작성하세요.

가능하면 3~5개의
핵심 Finding으로 압축하세요.

서로 비슷한 Finding은
하나로 통합하세요.

각 Finding에는
관련 Evidence를 연결하세요.


evidence_strength:

strong:
직접적이고 구체적인 발언이나
사례가 충분히 있음.

moderate:
관련 Evidence는 있으나
사례 또는 설명이 일부 부족함.

weak:
간접적 언급만 있고
해석의 불확실성이 큼.


==================================================
[Themes]
==================================================

Themes는
개별 답변 하나를 요약하는 영역이 아닙니다.

여러 질문 또는 여러 Evidence를
관통하는 상위 패턴을 찾으세요.

Key Findings와 동일한 문장을
다시 작성하지 마세요.

가능하면 2~4개로 제한하세요.

실제 반복 패턴이 없다면
빈 배열도 가능합니다.


==================================================
[Key Drivers]
==================================================

key_drivers는
응답자의 선택, 행동, 평가 또는
경험에 영향을 준 원인을 의미합니다.

Driver는 특정 제품 선호에
한정되지 않습니다.

예:

구매 요인
재방문 요인
만족 요인
불만 요인
도구 선택 요인
신뢰 형성 요인
업무 행동 요인

Evidence에서 원인 관계가
충분히 확인되지 않았다면
Driver로 만들지 마세요.

Key Findings 내용을
단순히 Driver로 복사하지 마세요.


==================================================
[Needs and Pain Points]
==================================================

needs_and_pain_points에는
실제 Evidence로 확인되는

pain_point
또는
need

만 작성하세요.


pain_point:
현재 경험에서 발생하는
불편, 문제, 마찰.

need:
응답자가 충족되기를 원하는
필요, 기대, 요구.


유사한 Pain Point는
하나로 합치세요.

예:

"반복적인 승인 요청"

과

"사용자가 계속 옆에서 확인해야 함"

이 동일한 원인에서 발생한다면
별개의 여러 항목으로 과도하게
분리하지 마세요.

근거 없는 심각도는
높게 평가하지 마세요.


==================================================
[Decision Dynamics]
==================================================

decision_dynamics는
이번 조사에서 다음과 같은
의사결정 행동이 실제로 중요할 때만 사용합니다.

선택
구매
유지
재이용
전환
이탈
채택
거부

그러한 내용이 없다면:

decision_dynamics = null

로 반환하세요.


current_state:
현재 응답자의 실제 선택이나 행동 상태.

decision_factors:
현재 판단에 영향을 주고 있다고
Evidence에서 확인되는 요인.

barriers:
행동 변화 또는 다른 선택을
방해하는 요인.

triggers:
행동 변화 가능성을 높일 수 있다고
응답자가 직접 또는 간접적으로
언급한 조건.


==================================================
[Behavioral Signal 엄격한 판단 규칙]
==================================================

behavioral_signal은
미래의 구매, 전환, 이탈,
재사용 등 행동 가능성에 대한
Evidence 강도를 의미합니다.

현재 제품을 좋아한다는 정도만으로
strong 또는 moderate를 주지 마세요.


strong:

응답자가 미래 행동 의사를
직접적이고 명확하게 표현함.

예:

"그 기능이 생기면 바로 바꿀 것이다."
"다음 구매에서도 반드시 선택할 것이다."
"이 문제가 계속되면 해지할 것이다."


moderate:

직접적인 확정 의사는 아니지만
구체적인 행동 조건과
실질적인 고려 의사가 확인됨.

예:

"그 기능이 생기면 다시 사용해볼 의향이 있다."
"가격이 내려가면 구매를 진지하게 고려할 것 같다."


weak:

호감, 기대, 불편 감소,
관심 정도만 확인됨.

예:

"그 기능이 있으면 훨씬 편할 것 같다."
"문제가 해결되면 더 좋아질 것 같다."


unclear:

미래 행동에 대한 Evidence가 없거나
판단하기 어려움.


매우 중요:

"답답함이 80% 줄 것 같다"

는

"그 제품으로 전환하겠다"

는 뜻이 아닙니다.

불편 감소에 대한 기대만으로
moderate 이상의 전환 신호를
부여하지 마세요.


==================================================
[Opportunities]
==================================================

opportunities는
실제 Evidence로 확인된
문제나 Need에서 출발해야 합니다.

소프트웨어 기능에만
한정하지 않습니다.


opportunity_type:

product
service
process
policy
communication
research
other


source_type:

explicit_user_request

응답자가 직접
구체적인 개선이나 해결책을 언급함.


derived_opportunity

응답자는 문제나 Need를 말했고
분석자가 해결 가능성을 도출함.


derived_opportunity를 작성할 때는
사용자가 직접 요청했다고
표현하지 마세요.

expected_value에는

"이 기능이 반드시 성과를 만든다"

처럼 확정적으로 쓰지 마세요.

Evidence에 맞게:

"반복 개입을 줄일 가능성이 있다."

"응답자가 느끼는 불편을 완화할 수 있다."

"추가 검증이 필요한 개선 방향이다."

처럼 작성하세요.


응답자가 숫자를 사용한 경우에도

"응답자는 자신의 불편 중
약 80%가 줄 것이라고 기대했다"

처럼 주관적 기대라는 점을
명확히 표시하세요.


==================================================
[Observer Intervention Analysis]
==================================================

observer_instructions가 있는 경우
Observer 개입의 실제 연구 가치를 평가합니다.

지시 이후
새로운 정보,
구체적 사례,
추가 Evidence가 실제로
확보됐는지 확인하세요.

resulting_evidence_ids에는
실제로 해당 개입 이후
확보된 Evidence만 연결하세요.

시간적으로 뒤에 나왔다는 이유만으로
모든 Evidence를 연결하지 마세요.

개입과 새로운 답변 사이의
내용상 연결성이 있어야 합니다.


research_value:

high:
중요한 새로운 사례나
연구 판단에 필요한 정보가 확보됨.

medium:
일부 구체화 또는 보완이 이루어짐.

low:
새로운 연구 정보가 거의 추가되지 않음.


==================================================
[Researcher Attention]
==================================================

researcher_attention에는
다음 인터뷰나 후속 조사에서
실제로 확인할 가치가 높은 내용만 작성하세요.

예:

Coverage가 낮은 중요한 Slot
모호하게 남은 발언
행동 의향과 실제 행동의 차이
구체적인 조건이나 맥락
Opportunity 검증에 필요한 정보

이미 충분히 확보된 정보를
다시 물어보라고 제안하지 마세요.

가능하면 가장 중요한
2~5개로 제한하세요.


==================================================
[최종 품질 점검]
==================================================

출력 전에 스스로 확인하세요.

1.
응답자가 말하지 않은 내용을
추가하지 않았는가?

2.
질문의 유도 문구를
응답자의 의견으로 착각하지 않았는가?

3.
동일한 내용을
Key Findings, Themes, Drivers에서
불필요하게 반복하지 않았는가?

4.
한 명의 응답을
전체 사용자나 시장으로
일반화하지 않았는가?

5.
응답자의 주관적인 숫자를
객관적 성과 수치처럼
표현하지 않았는가?

6.
behavioral_signal을
실제 행동 Evidence보다
과도하게 높이지 않았는가?

7.
각 중요한 분석에
실제 evidence_id가 존재하는가?


==================================================
[출력 규칙]
==================================================

제공된 JSON Schema를
정확히 따라야 합니다.

Schema에 없는 필드를
추가하지 마세요.

필수 필드를
누락하지 마세요.

관련 없는 섹션은
억지로 내용을 만들어 채우지 말고

빈 배열 또는
Schema에서 허용된 null

을 사용하세요.
"""

        # =================================================
        # 5. Pydantic → JSON Schema
        # =================================================

        output_schema = (
            IndividualInterviewAnalysis
            .model_json_schema()
        )

        # =================================================
        # 6. GPT-5.1 Structured Output
        # =================================================

        try:

            response = (
                await self._client.responses.create(
                    model=self._deployment,

                    instructions=system_prompt,

                    input=(
                        "아래 조사 및 인터뷰 데이터를 "
                        "분석하세요.\n\n"
                        "이번 조사의 목적과 질문에만 "
                        "맞춰 분석하고 특정 산업이나 "
                        "제품 유형을 가정하지 마세요.\n\n"
                        "required_slots가 존재하면 "
                        "모든 Slot을 정확히 하나씩 "
                        "평가하세요.\n\n"
                        "동일한 내용을 여러 분석 섹션에서 "
                        "불필요하게 반복하지 마세요.\n\n"
                        "미래 행동 의사가 명확하지 않다면 "
                        "behavioral_signal을 보수적으로 "
                        "판단하세요.\n\n"
                        "응답자의 숫자나 비율 표현은 "
                        "객관적인 제품 성과가 아니라 "
                        "개인의 주관적 기대라는 점을 "
                        "유지하세요.\n\n"
                        + json.dumps(
                            input_data,
                            ensure_ascii=False,
                            indent=2,
                        )
                    ),

                    reasoning={
                        "effort": "none"
                    },

                    max_output_tokens=12000,

                    text={
                        "verbosity": "low",

                        "format": {
                            "type": "json_schema",

                            "name": (
                                "individual_"
                                "interview_analysis"
                            ),

                            "schema": (
                                output_schema
                            ),

                            "strict": True,
                        },
                    },
                )
            )

        except Exception:

            logger.exception(
                "Azure OpenAI 리포트 분석 호출 실패"
            )

            raise

        # =================================================
        # 7. 응답 확인
        # =================================================

        content = response.output_text

        if not content:
            raise ValueError(
                "Azure OpenAI가 빈 분석 결과를 "
                "반환했습니다."
            )

        # =================================================
        # 8. JSON Parsing
        # =================================================

        try:

            raw_result = json.loads(
                content
            )

        except json.JSONDecodeError:

            logger.exception(
                "Azure OpenAI 결과 JSON 파싱 실패. "
                "응답 앞부분=%s",
                content[:500],
            )

            raise

        # =================================================
        # 9. Evidence ID 검증
        # =================================================

        self._sanitize_evidence_ids(
            raw_result,
            allowed_evidence_ids,
        )

        # =================================================
        # 10. Dynamic Slot 검증
        # =================================================

        self._validate_slots(
            result=raw_result,
            required_slots=required_slots,
        )

        # =================================================
        # 11. Pydantic 최종 검증
        # =================================================

        validated = (
            IndividualInterviewAnalysis
            .model_validate(
                raw_result
            )
        )

        return validated.model_dump(
            mode="json"
        )


    # =====================================================
    # Evidence ID 검증
    # =====================================================

    def _sanitize_evidence_ids(
        self,
        value: Any,
        allowed_evidence_ids: set[str],
    ) -> None:

        if isinstance(value, dict):

            for key, item in value.items():

                if (
                    key in {
                        "evidence_ids",
                        "resulting_evidence_ids",
                    }
                    and isinstance(
                        item,
                        list,
                    )
                ):

                    value[key] = [
                        evidence_id
                        for evidence_id
                        in item
                        if evidence_id
                        in allowed_evidence_ids
                    ]

                else:

                    self._sanitize_evidence_ids(
                        item,
                        allowed_evidence_ids,
                    )

        elif isinstance(value, list):

            for item in value:

                self._sanitize_evidence_ids(
                    item,
                    allowed_evidence_ids,
                )


    # =====================================================
    # Dynamic Slot 검증
    # =====================================================

    def _validate_slots(
        self,
        result: dict[str, Any],
        required_slots: list[
            dict[str, Any]
        ],
    ) -> None:

        required_ids = [
            slot["slot_id"]
            for slot in required_slots
        ]

        items = (
            result
            .get(
                "slot_coverage",
                {},
            )
            .get(
                "items",
                [],
            )
        )

        result_ids = [
            item.get("slot_id")
            for item in items
        ]

        # Study Slot 없는 legacy Session
        if not required_ids:

            if result_ids:
                raise ValueError(
                    "Study Slot이 없는데 "
                    "새로운 Slot이 생성되었습니다."
                )

            return

        missing = (
            set(required_ids)
            - set(result_ids)
        )

        unexpected = (
            set(result_ids)
            - set(required_ids)
        )

        duplicates = {
            slot_id
            for slot_id in result_ids
            if result_ids.count(
                slot_id
            ) > 1
        }

        if missing:
            raise ValueError(
                "누락된 Slot: "
                f"{sorted(missing)}"
            )

        if unexpected:
            raise ValueError(
                "정의되지 않은 Slot: "
                f"{sorted(unexpected)}"
            )

        if duplicates:
            raise ValueError(
                "중복된 Slot: "
                f"{sorted(duplicates)}"
            )

        if (
            len(result_ids)
            != len(required_ids)
        ):
            raise ValueError(
                "Slot 개수가 ResearchStudy에 "
                "저장된 Slot 개수와 일치하지 않습니다."
            )


# =========================================================
# Analyzer Singleton
# =========================================================

_analyzer: ReportAnalyzer | None = None


def get_report_analyzer() -> ReportAnalyzer:

    global _analyzer

    if _analyzer is None:

        settings = get_settings()

        if settings.use_azure_openai:

            logger.info(
                "AzureOpenAIReportAnalyzer 사용"
            )

            _analyzer = (
                AzureOpenAIReportAnalyzer()
            )

        else:

            logger.warning(
                "Azure OpenAI 설정 없음 - "
                "StubReportAnalyzer 사용"
            )

            _analyzer = (
                StubReportAnalyzer()
            )

    return _analyzer