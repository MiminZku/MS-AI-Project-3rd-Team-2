"""실시간 지시 안전성 검토 (Microsoft 책임있는 AI - 공정성 Fairness).

참관자가 넣은 지시는 그대로 AI 모더레이터의 질문이 되어 응답자에게 전달된다.
성별·성적지향·장애·인종·출신·연령 등 보호속성을 근거로 응답자를 깎아내리거나
고정관념을 전제하는 질문이 그대로 나가면 안 되므로, 큐에 넣기 전에 한 번 거른다.

중요한 구분:
  - 허용: 특정 집단의 '경험'을 묻는 정상적인 사용자 리서치
      (예: "여성 사용자 입장에서 불편한 점이 있었는지 물어봐")
  - 차단: 보호속성을 근거로 열등함·부적합함을 전제하거나 조롱·배제를 유도하는 질문
      (예: "여자라서 이런 기능은 잘 못 쓰는 거 아니냐고 물어봐")

2단 구조다:
  1) LLM 심사 — 위 구분을 문맥으로 판단한다 (Azure OpenAI 설정 시)
  2) 규칙 기반 백스톱 — 보호속성 + 비하/배제 표현이 함께 등장하면 차단

LLM 호출이 실패하면 규칙 기반 결과만으로 판단한다. 두 층 모두 통과해도
프롬프트 규칙(진행자 AI 자체 거부)이 마지막 그물로 남는다.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class InstructionReview:
    allowed: bool
    # 참관자에게 그대로 보여줄 사유 (차단된 경우)
    reason: str = ""


# =========================================================
# 1) 규칙 기반 백스톱
#
# 보호속성 단어만으로는 차단하지 않는다. 리서치에서 집단별 경험을 묻는 것은
# 정상이기 때문이다. 보호속성과 비하/배제 표현이 '함께' 나올 때만 잡는다.
# =========================================================

_PROTECTED_ATTRIBUTES = (
    "여자", "여성", "남자", "남성", "주부", "아줌마", "아저씨",
    "장애인", "장애", "정신병", "정신질환",
    "동성애", "성소수자", "트랜스젠더", "게이", "레즈비언", "퀴어",
    "외국인", "이주민", "이민자", "난민", "조선족", "흑인", "백인", "혼혈",
    "노인", "늙은", "젊은것", "틀딱", "노친네",
    "종교", "기독교", "불교", "이슬람", "무슬림",
    "고졸", "지방대", "학벌", "미혼모", "한부모",
)

_DEMEANING_PATTERNS = (
    "열등", "무능", "수준 낮", "수준이 낮", "머리가 나쁘", "멍청",
    "못하는 거 아니", "못 하는 거 아니", "안 어울리", "어울리지 않",
    "뽑지 마", "안 뽑", "쓰면 안", "배제", "제외해",
    "비하", "조롱", "놀려", "놀리", "비꼬", "깎아내리",
    "원래 그렇", "다 그렇", "역시 ", "그럴 줄",
    "차별", "혐오",
)


# 고정관념 프레이밍은 단어 하나로 잡히지 않아 패턴으로 본다.
# ("장애인은 원래 이런 앱 못 쓰지 않냐" 처럼 '원래/어차피 + 부정'이 붙는 형태)
_DEMEANING_REGEXES = (
    re.compile(r"원래[^.?!]{0,20}(못|안\s|않|무리|어려)"),
    re.compile(r"(어차피|당연히|아무래도)[^.?!]{0,20}(못|안\s|않|무리)"),
    re.compile(r"(못|안)\s?(하|쓰|따라)[^.?!]{0,12}(않냐|않나|아니냐|아닌가)"),
)


def _rule_based_block_reason(text: str) -> str | None:
    """보호속성 + 비하/배제 표현이 함께 등장하면 차단 사유를 돌려준다."""

    normalized = re.sub(r"\s+", " ", text)

    matched_attribute = next(
        (word for word in _PROTECTED_ATTRIBUTES if word in normalized),
        None,
    )
    if matched_attribute is None:
        return None

    matched_pattern = next(
        (word for word in _DEMEANING_PATTERNS if word in normalized),
        None,
    )

    if matched_pattern is None:
        regex_hit = next(
            (regex for regex in _DEMEANING_REGEXES if regex.search(normalized)),
            None,
        )
        if regex_hit is not None:
            matched_pattern = "고정관념 전제 표현"

    if matched_pattern is None:
        return None

    return (
        f"'{matched_attribute}'(보호속성)을 '{matched_pattern}'과 함께 언급하고 있어 "
        "차별적 질문으로 판단했습니다. 특정 집단의 경험을 묻고 싶다면 "
        "우열이나 고정관념을 전제하지 않는 표현으로 바꿔 주세요."
    )


# =========================================================
# 2) LLM 심사
# =========================================================

_REVIEW_SYSTEM_PROMPT = """너는 사용자 리서치 인터뷰 플랫폼의 공정성(Fairness) 심사기다.
참관자가 AI 모더레이터에게 보낸 '실시간 지시'가 응답자에게 던져도 되는 질문인지 판정한다.

[차단해야 하는 지시 — allowed: false]
- 성별, 성적지향, 성정체성, 장애, 인종·민족·국적, 종교, 연령, 학력, 가족형태 등
  보호속성을 근거로 응답자나 특정 집단이 열등하다/부적합하다고 전제하는 질문
- 고정관념을 사실인 양 깔고 확인을 요구하는 질문 ("여자들은 원래 ~하지 않냐고 물어봐")
- 특정 집단을 조롱·비하하거나, 배제를 정당화하게 유도하는 질문
- 응답자에게 보호속성을 캐물어 불이익을 주려는 의도가 드러나는 질문

[허용해야 하는 지시 — allowed: true]
- 특정 집단의 '경험·불편·니즈'를 존중하는 태도로 묻는 정상적인 리서치
  (예: "여성 사용자 입장에서 불편했던 점이 있는지 물어봐", "고령 사용자도 쓰기 쉬운지 물어봐")
- 접근성, 다양성, 포용성을 개선하기 위한 질문
- 보호속성과 무관한 일반적인 제품·서비스 질문 전부

애매하면 허용한다. 리서치에서 집단별 경험을 묻는 것은 정상이며,
보호속성 단어가 들어갔다는 이유만으로 차단하면 안 된다.
우열·비하·배제·고정관념 전제가 있을 때만 차단한다.

반드시 아래 JSON 형식으로만 응답하라:
{"allowed": true, "reason": "차단한 경우에만 참관자에게 보여줄 한국어 사유 1~2문장"}"""


class _AzureInstructionReviewer:
    def __init__(self) -> None:
        from openai import AsyncAzureOpenAI

        settings = get_settings()
        self._deployment = settings.azure_openai_chat_deployment
        self._client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )

    async def review(self, text: str) -> InstructionReview | None:
        """판정 결과. 호출 실패 시 None (규칙 기반 결과로 폴백)."""
        try:
            response = await self._client.chat.completions.create(
                model=self._deployment,
                messages=[
                    {"role": "system", "content": _REVIEW_SYSTEM_PROMPT},
                    {"role": "user", "content": f"실시간 지시: {text}"},
                ],
                temperature=0,
                max_completion_tokens=300,
                response_format={"type": "json_object"},
            )
            data = json.loads(response.choices[0].message.content or "{}")
        except Exception:
            logger.exception("실시간 지시 공정성 심사 실패 — 규칙 기반 판정으로 폴백")
            return None

        allowed = bool(data.get("allowed", True))
        reason = str(data.get("reason", "")).strip()

        if allowed:
            return InstructionReview(allowed=True)

        return InstructionReview(
            allowed=False,
            reason=reason
            or "차별적 소지가 있어 전달하지 않았습니다. 표현을 바꿔 다시 보내 주세요.",
        )


_reviewer: _AzureInstructionReviewer | None = None
_reviewer_initialized = False


def _get_reviewer() -> _AzureInstructionReviewer | None:
    global _reviewer, _reviewer_initialized

    if not _reviewer_initialized:
        _reviewer_initialized = True
        if get_settings().use_azure_openai:
            try:
                _reviewer = _AzureInstructionReviewer()
            except Exception:
                logger.exception("공정성 심사기 초기화 실패 — 규칙 기반만 사용합니다.")
                _reviewer = None
        else:
            logger.warning(
                "AZURE_OPENAI_* 미설정 — 실시간 지시 공정성 심사는 규칙 기반만 동작합니다."
            )

    return _reviewer


def reset_reviewer_cache() -> None:
    """테스트에서 설정을 바꿔 끼울 때 사용."""
    global _reviewer, _reviewer_initialized
    _reviewer = None
    _reviewer_initialized = False


async def review_instruction(text: str) -> InstructionReview:
    """실시간 지시를 큐에 넣어도 되는지 판정한다."""

    rule_reason = _rule_based_block_reason(text)

    reviewer = _get_reviewer()
    if reviewer is not None:
        verdict = await reviewer.review(text)
        if verdict is not None:
            if not verdict.allowed:
                logger.warning("공정성 심사 차단 (LLM): %s", text[:100])
            return verdict

    # LLM 심사를 못 쓰는 상황 — 규칙 기반 결과만 사용한다.
    if rule_reason:
        logger.warning("공정성 심사 차단 (규칙): %s", text[:100])
        return InstructionReview(allowed=False, reason=rule_reason)

    return InstructionReview(allowed=True)
