"""종합 리포트 입력 구성 — 개별 리포트 LLM 단계 제거 회귀 테스트.

개별 리포트는 더 이상 산출물이 아니다. 예전에는 세션마다 개별 리포트를
LLM으로 먼저 만들어 종합 분석에 넣었는데, 그 때문에
  - 응답자 수만큼 LLM 호출이 늘어 생성이 수 분씩 걸렸고
  - 개별 분석기의 엄격한 Slot 검증이 실패하면 종합 리포트까지 통째로 막혔다.

이제 전사(응답자 발화)에서 바로 근거를 만들어 종합 분석기에 넘긴다.
"""

from app.schemas.session import QuestionNode, Session, Turn
from app.services.project_report import _participant_reports_from_transcripts
from app.services.report.study_analyzer import StudyReportAnalyzer


def _session(session_id: str, title: str) -> Session:
    return Session(
        id=session_id,
        title=title,
        status="ended",
        questions=[QuestionNode(id="q1", order=1, text="질문?")],
    )


def _turns(*pairs: tuple[str, str]) -> list[Turn]:
    return [
        Turn(index=index, speaker=speaker, text=text)
        for index, (speaker, text) in enumerate(pairs)
    ]


def test_응답자_발화만_근거로_뽑는다():
    sessions = [_session("ses_1", "P01")]
    transcripts = {
        "ses_1": _turns(
            ("assistant", "요즘 어떤 도구를 쓰시나요?"),
            ("interviewee", "주로 클로드를 씁니다."),
            ("assistant", "이유가 있을까요?"),
            ("interviewee", "복잡한 리팩터링에 강해서요."),
        )
    }

    reports = _participant_reports_from_transcripts(sessions, transcripts)

    assert len(reports) == 1
    evidence = reports[0]["data"]["evidence"]
    quotes = [item["quote"] for item in evidence]
    # AI 진행자 발화는 근거가 아니다
    assert quotes == ["주로 클로드를 씁니다.", "복잡한 리팩터링에 강해서요."]
    assert [item["evidence_id"] for item in evidence] == ["E001", "E002"]


def test_PM이_입력한_참가자_ID를_그대로_쓴다():
    sessions = [_session("ses_1", "P07-김민수")]
    transcripts = {"ses_1": _turns(("interviewee", "네 그렇습니다."))}

    reports = _participant_reports_from_transcripts(sessions, transcripts)

    assert reports[0]["participant_id"] == "P07-김민수"
    assert reports[0]["session_id"] == "ses_1"


def test_발화가_없는_세션은_제외한다():
    """근거 없는 참여자를 넣으면 종합 분석기 검증에서 통째로 실패한다."""
    sessions = [_session("ses_1", "P01"), _session("ses_2", "P02")]
    transcripts = {
        "ses_1": _turns(("assistant", "질문만 하고 끝난 세션")),
        "ses_2": _turns(("interviewee", "답변이 있는 세션")),
    }

    reports = _participant_reports_from_transcripts(sessions, transcripts)

    assert [report["participant_id"] for report in reports] == ["P02"]


def test_공백만_있는_발화는_근거가_아니다():
    sessions = [_session("ses_1", "P01")]
    transcripts = {
        "ses_1": _turns(("interviewee", "   "), ("interviewee", "실제 답변"))
    }

    reports = _participant_reports_from_transcripts(sessions, transcripts)

    assert [item["quote"] for item in reports[0]["data"]["evidence"]] == ["실제 답변"]


def test_참가자_ID가_겹치면_구분한다():
    """중복 participant_id는 종합 분석기가 ValueError로 거부한다."""
    sessions = [_session("ses_1", "P01"), _session("ses_2", "P01")]
    transcripts = {
        "ses_1": _turns(("interviewee", "첫 번째")),
        "ses_2": _turns(("interviewee", "두 번째")),
    }

    reports = _participant_reports_from_transcripts(sessions, transcripts)

    ids = [report["participant_id"] for report in reports]
    assert len(set(ids)) == 2


def test_제목이_비면_순번으로_채운다():
    sessions = [_session("ses_1", "")]
    transcripts = {"ses_1": _turns(("interviewee", "답변"))}

    reports = _participant_reports_from_transcripts(sessions, transcripts)

    assert reports[0]["participant_id"] == "P01"


def test_종합_분석기_정규화를_실제로_통과한다():
    """만든 입력이 StudyReportAnalyzer가 받아들이는 형태인지 확인한다."""
    sessions = [_session("ses_1", "P01"), _session("ses_2", "P02")]
    transcripts = {
        "ses_1": _turns(("interviewee", "첫 응답자 발화")),
        "ses_2": _turns(("interviewee", "두 번째 응답자 발화")),
    }

    reports = _participant_reports_from_transcripts(sessions, transcripts)

    analyzer = object.__new__(StudyReportAnalyzer)
    normalized = analyzer._normalize_participant_reports(reports)

    assert [item["participant_id"] for item in normalized] == ["P01", "P02"]
    # Study 단위에서 충돌하지 않도록 참여자 접두사가 붙어야 한다
    assert normalized[0]["evidence"][0]["evidence_id"] == "P01_E001"
    assert normalized[1]["evidence"][0]["evidence_id"] == "P02_E001"


def test_파이프라인이_개별_리포트_분석기를_더는_쓰지_않는다():
    """개별 분석기의 Slot 검증이 종합 리포트를 막던 경로가 사라졌는지 확인한다."""
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "services"
        / "project_report.py"
    ).read_text(encoding="utf-8")

    assert "individual_report_generator" not in source
