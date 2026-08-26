"""프로젝트 종합 리포트 재시도 — 실제 경로 검증.

test_study_report_retry.py 는 `_generate_once` 자체를 목으로 바꿔서 재시도 루프의
'모양'만 확인한다. 이 파일은 그 아래 실제 코드를 전부 태운다:

    analyze()
      -> input_payload 구성
      -> create_structured_json (LLM 경계만 가짜)
      -> json.loads / model_validate
      -> _replace_overview / _replace_evidence_library / _sanitize_segment_differences
      -> _validate_result   <-- 실제로 "Evidence가 없습니다"를 던지는 곳
      -> 검증 실패시 재시도

즉 실제로 사용자가 겪은 오류(executive_summary.key_takeaways[N]: Evidence가 없습니다)를
그대로 재현하고, 재시도로 복구되는지 확인한다.
"""

import copy
import json
from pathlib import Path

import pytest

from app.schemas.study import ResearchStudy
from app.services.report import study_analyzer as study_analyzer_module
from app.services.report.study_analyzer import StudyReportAnalyzer

# 실제 스키마를 만족하는 종합 리포트 샘플 (참여자 P01/P02, evidence P01_E001~P02_E004)
FIXTURE = Path(__file__).resolve().parents[1] / "app" / "ai-interview-report" / "study_report.json"


def _good_report() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _report_missing_evidence() -> dict:
    """사용자가 실제로 만난 상태: key_takeaways 한 항목의 evidence_ids가 비어 있다."""
    broken = _good_report()
    broken["executive_summary"]["key_takeaways"][0]["evidence_ids"] = []
    return broken


def _analyzer() -> StudyReportAnalyzer:
    """Azure 자격 증명 없이 분석 로직만 태우기 위해 __init__을 건너뛴다."""
    analyzer = object.__new__(StudyReportAnalyzer)
    analyzer.client = object()
    analyzer.deployment = "gpt-4o"
    return analyzer


def _study() -> ResearchStudy:
    return ResearchStudy(
        id="study_9783192abd01",
        title="배송 경험 자동화 최종 테스트",
        research_purpose="온라인 쇼핑 배송 과정에서 사용자가 느끼는 불편과 개선 요구를 파악한다.",
        question_script="1. 최근 배송 경험은 어땠나요?\n2. 불편했던 점은?\n3. 개선 요구는?",
    )


def _participant_reports() -> list[dict]:
    """정규화하면 P01_E001.. / P02_E001.. 형태가 되도록 맞춘 개별 리포트 입력."""
    fixture = _good_report()
    reports: list[dict] = []
    for participant in ("P01", "P02"):
        evidence = [
            {
                # 정규화 단계에서 참여자 접두사가 붙으므로 여기서는 E001 형태로 넣는다
                "evidence_id": item["evidence_id"].split("_", 1)[1],
                "quote": item["quote"],
                "question_id": item.get("question_id"),
            }
            for item in fixture["evidence"]
            if item["participant_id"] == participant
        ]
        reports.append({"data": {"evidence": evidence}})
    return reports


def _install_fake_llm(monkeypatch, responses: list[dict]) -> list[dict]:
    """create_structured_json 을 가짜로 바꾸고, 호출 인자를 기록해 돌려준다."""
    calls: list[dict] = []
    queue = list(responses)

    async def fake_create_structured_json(_client, **kwargs):
        calls.append(kwargs)
        return json.dumps(queue.pop(0), ensure_ascii=False)

    monkeypatch.setattr(
        study_analyzer_module,
        "create_structured_json",
        fake_create_structured_json,
    )
    return calls


# =========================================================
# 고치기 전 상태 재현
# =========================================================

async def test_evidence_누락은_실제로_검증에서_걸린다(monkeypatch):
    """재시도가 의미 있으려면, 먼저 이 오류가 진짜로 발생해야 한다."""
    analyzer = _analyzer()
    _install_fake_llm(monkeypatch, [_report_missing_evidence()] * 3)

    with pytest.raises(ValueError, match=r"key_takeaways\[1\].*Evidence가 없습니다"):
        await analyzer.analyze(_study(), _participant_reports())


# =========================================================
# 고친 뒤 동작
# =========================================================

async def test_첫_시도가_실패해도_재시도로_리포트가_완성된다(monkeypatch):
    analyzer = _analyzer()
    calls = _install_fake_llm(
        monkeypatch,
        [_report_missing_evidence(), _good_report()],
    )

    result = await analyzer.analyze(_study(), _participant_reports())

    # 실제 스키마 객체가 나와야 한다
    assert result.overview.participant_count == 2
    assert len(result.executive_summary.key_takeaways) == 3
    assert all(item.evidence_ids for item in result.executive_summary.key_takeaways)

    assert len(calls) == 2


async def test_재시도_프롬프트에_직전_실패_사유가_실린다(monkeypatch):
    analyzer = _analyzer()
    calls = _install_fake_llm(
        monkeypatch,
        [_report_missing_evidence(), _good_report()],
    )

    await analyzer.analyze(_study(), _participant_reports())

    first_input = calls[0]["user_input"]
    second_input = calls[1]["user_input"]

    assert "previous_attempt_validation_error" not in first_input
    assert "previous_attempt_validation_error" in second_input
    assert "Evidence가 없습니다" in second_input


async def test_재시도할수록_temperature가_올라간다(monkeypatch):
    """온도를 0으로 고정한 채 재시도하면 같은 답이 다시 나와 재시도가 무의미해진다."""
    analyzer = _analyzer()
    calls = _install_fake_llm(monkeypatch, [_report_missing_evidence()] * 3)

    with pytest.raises(ValueError):
        await analyzer.analyze(_study(), _participant_reports())

    temperatures = [call["temperature"] for call in calls]
    assert temperatures == [0.0, 0.4, 0.7]
    assert temperatures == sorted(temperatures)
    assert len(set(temperatures)) == 3


async def test_정상_응답이면_한_번만_호출한다(monkeypatch):
    """불필요한 재호출로 비용이 늘면 안 된다."""
    analyzer = _analyzer()
    calls = _install_fake_llm(monkeypatch, [_good_report()])

    result = await analyzer.analyze(_study(), _participant_reports())

    assert len(calls) == 1
    assert result.overview.participant_count == 2


async def test_evidence_없는_항목을_아예_뺀_응답도_통과한다(monkeypatch):
    """프롬프트가 권장하는 대응(항목 제외)이 실제로 검증을 통과하는지 확인한다."""
    analyzer = _analyzer()
    trimmed = _good_report()
    trimmed["executive_summary"]["key_takeaways"] = trimmed["executive_summary"][
        "key_takeaways"
    ][1:]
    calls = _install_fake_llm(monkeypatch, [_report_missing_evidence(), trimmed])

    result = await analyzer.analyze(_study(), _participant_reports())

    assert len(calls) == 2
    assert len(result.executive_summary.key_takeaways) == 2


# =========================================================
# 프롬프트 규칙
# =========================================================

def test_시스템_프롬프트가_빈_evidence를_금지한다():
    prompt = _analyzer()._build_system_prompt()

    assert "evidence_ids를 절대 빈 배열로 남기면 안 됩니다" in prompt
    assert "목록에서 제외하세요" in prompt


def test_고정된_fixture가_스키마를_만족한다():
    """이 테스트 파일의 전제(샘플이 유효하다)가 깨지면 바로 알 수 있게 한다."""
    from app.schemas.study_report import StudyReportAnalysis

    assert StudyReportAnalysis.model_validate(_good_report())
