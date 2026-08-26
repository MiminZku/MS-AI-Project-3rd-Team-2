"""프로젝트 종합 리포트: evidence 누락 검증 실패 시 자동 재시도.

실측 회귀: 리포트 생성을 누르면
"executive_summary.key_takeaways[1]: Evidence가 없습니다."
라는 오류로 리포트 생성 전체가 실패했다.

원인: StudyReportAnalyzer._validate_result()가 key_takeaways 등 여러 섹션에
대해 "각 항목은 evidence_ids를 1개 이상 가져야 한다"는 비즈니스 규칙을
엄격히 검사하는데, 이건 JSON Schema로 강제되는 값이 아니라 모델이 가끔
빈 배열을 낼 수 있다. 재시도 없이 바로 실패시켜서, 응답자가 적은(3명) Study는
같은 이유로 매번 실패하곤 했다.
"""

import pytest

from app.schemas.study import ResearchStudy
from app.services.report.study_analyzer import StudyReportAnalyzer


def _analyzer() -> StudyReportAnalyzer:
    """Azure 자격 증명 없이 재시도 루프만 단위 테스트하기 위해 __init__을 건너뛴다."""
    return object.__new__(StudyReportAnalyzer)


def _study() -> ResearchStudy:
    return ResearchStudy(
        title="테스트 프로젝트",
        research_purpose="목적",
        question_script="1. 질문?",
    )


async def test_evidence_누락으로_실패하면_피드백과_함께_재시도한다(monkeypatch):
    analyzer = _analyzer()
    calls: list[str | None] = []

    async def fake_generate_once(*, study, normalized_reports, retry_feedback, temperature):
        calls.append(retry_feedback)
        if len(calls) == 1:
            raise ValueError(
                "executive_summary.key_takeaways[1]: Evidence가 없습니다."
            )
        return "완성된-리포트"

    monkeypatch.setattr(analyzer, "_generate_once", fake_generate_once)

    result = await analyzer.analyze(_study(), [{"session_id": "s1"}])

    assert result == "완성된-리포트"
    assert len(calls) == 2
    # 첫 시도는 피드백 없이, 재시도는 직전 오류 내용을 담아 보낸다
    assert calls[0] is None
    assert calls[1] is not None
    assert "Evidence가 없습니다" in calls[1]


async def test_재시도_횟수를_다_쓰면_마지막_오류를_그대로_올린다(monkeypatch):
    analyzer = _analyzer()
    call_count = 0

    async def always_fails(*, study, normalized_reports, retry_feedback, temperature):
        nonlocal call_count
        call_count += 1
        raise ValueError(f"실패 {call_count}회차")

    monkeypatch.setattr(analyzer, "_generate_once", always_fails)

    with pytest.raises(ValueError, match=r"실패 3회차"):
        await analyzer.analyze(_study(), [{"session_id": "s1"}])

    # 최초 1회 + 재시도 2회 = 총 3회 시도하고 포기한다
    assert call_count == analyzer.MAX_VALIDATION_RETRIES + 1


async def test_JSON_파싱_실패_같은_기술적_오류는_재시도하지_않는다(monkeypatch):
    """ValueError(비즈니스 규칙 위반)만 재시도한다. RuntimeError는 같은 결과가 반복될
    가능성이 커서 즉시 올린다."""
    analyzer = _analyzer()
    call_count = 0

    async def technical_failure(*, study, normalized_reports, retry_feedback, temperature):
        nonlocal call_count
        call_count += 1
        raise RuntimeError("Study 종합 분석 결과가 비어 있습니다.")

    monkeypatch.setattr(analyzer, "_generate_once", technical_failure)

    with pytest.raises(RuntimeError):
        await analyzer.analyze(_study(), [{"session_id": "s1"}])

    assert call_count == 1


async def test_참여자_리포트가_없으면_재시도_없이_즉시_실패한다():
    analyzer = _analyzer()

    with pytest.raises(ValueError, match="participant_reports가 없습니다"):
        await analyzer.analyze(_study(), [])
