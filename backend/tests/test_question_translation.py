"""질문 번역 + 오프닝 인사 기록 회귀 테스트.

실측 불만:
  - 리포트/참관자 대시보드에서 **질문 쪽이 번역되지 않는다**.
    해외 클라이언트가 참관할 때 지금 무슨 질문인지 알 수 없다.
  - 인터뷰 시작 시 AI 진행자의 오프닝 인사가 실시간 진행 상황에 안 보인다.
    (응답자 화면이 자체적으로 발화해 백엔드를 거치지 않았다)
"""

from app.schemas.session import QuestionNode, Session
from app.services.ai import translation as translation_module
from app.services.ai.translation import translate_assistant_text, translate_questions

SCRIPT = """
1. 요즘 어떤 AI 도구를 쓰시나요?
   [클로드] → 클로드를 고른 이유가 있을까요?
2. 하루에 얼마나 오래 쓰시나요?
"""

MAIN_QUESTION = "요즘 어떤 AI 도구를 쓰시나요?"
BRANCH_QUESTION = "클로드를 고른 이유가 있을까요?"


def _questions() -> list[QuestionNode]:
    return [
        QuestionNode(
            id="q1",
            order=1,
            text=MAIN_QUESTION,
            branches={"클로드": BRANCH_QUESTION},
        ),
        QuestionNode(id="q2", order=2, text="하루에 얼마나 오래 쓰시나요?"),
    ]


class _FakeTranslator:
    """번역기를 흉내낸다 — 실제 LLM 호출 없이 경로만 태운다."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def translate(self, text: str, *, target_language: str) -> str:
        self.calls.append((text, target_language))
        return f"[{target_language}] {text}"


def _install_translator(monkeypatch) -> _FakeTranslator:
    fake = _FakeTranslator()
    monkeypatch.setattr(translation_module, "_translator", fake)
    monkeypatch.setattr(translation_module, "_initialized", True)
    return fake


def _create_session(client, *, language: str = "en") -> dict:
    response = client.post(
        "/api/sessions",
        json={
            "title": "P01",
            "duration_minutes": 20,
            "interpretation_language": language,
            "question_script": SCRIPT,
        },
    )
    assert response.status_code == 201
    return response.json()["session"]


# =========================================================
# 질문 번역 (세션 생성 시 1회)
# =========================================================

async def test_질문과_파생질문이_모두_번역된다(monkeypatch):
    _install_translator(monkeypatch)
    questions = _questions()

    await translate_questions(questions, target_language_code="en")

    assert questions[0].text_translated == f"[English] {MAIN_QUESTION}"
    assert questions[0].branches_translated["클로드"] == f"[English] {BRANCH_QUESTION}"
    assert questions[1].text_translated == "[English] 하루에 얼마나 오래 쓰시나요?"


async def test_통역_언어가_원문과_같으면_번역하지_않는다(monkeypatch):
    """한국어 인터뷰를 한국어로 다시 번역하는 낭비를 막는다."""
    fake = _install_translator(monkeypatch)
    questions = _questions()

    await translate_questions(questions, target_language_code="ko")

    assert fake.calls == []
    assert questions[0].text_translated is None


async def test_번역기가_없어도_세션_생성을_막지_않는다(monkeypatch):
    monkeypatch.setattr(translation_module, "_translator", None)
    monkeypatch.setattr(translation_module, "_initialized", True)
    questions = _questions()

    await translate_questions(questions, target_language_code="en")

    assert questions[0].text_translated is None


def test_세션_생성시_질문이_번역되어_저장된다(client, monkeypatch):
    _install_translator(monkeypatch)

    session = _create_session(client)
    question = session["questions"][0]

    assert question["text_translated"].startswith("[English]")
    assert question["branches_translated"]["클로드"].startswith("[English]")

    # DB에 저장되어 이후 조회에서도 그대로 나와야 한다
    stored = client.get(f"/api/sessions/{session['id']}").json()["session"]
    assert stored["questions"][0]["text_translated"] == question["text_translated"]


# =========================================================
# AI 진행자 발화 번역 (인터뷰 중)
# =========================================================

async def test_대본_질문은_미리_번역해둔_값을_재사용한다(monkeypatch):
    """매 턴 LLM을 다시 부르면 느리고 비싸다."""
    fake = _install_translator(monkeypatch)
    questions = _questions()
    await translate_questions(questions, target_language_code="en")
    calls_after_setup = len(fake.calls)

    session = Session(title="P01", interpretation_language="en", questions=questions)

    result = await translate_assistant_text(session, MAIN_QUESTION)

    assert result == f"[English] {MAIN_QUESTION}"
    # 추가 번역 호출이 없어야 한다
    assert len(fake.calls) == calls_after_setup


async def test_파생질문도_미리_번역해둔_값을_쓴다(monkeypatch):
    fake = _install_translator(monkeypatch)
    questions = _questions()
    await translate_questions(questions, target_language_code="en")
    calls_after_setup = len(fake.calls)

    session = Session(title="P01", interpretation_language="en", questions=questions)

    result = await translate_assistant_text(session, BRANCH_QUESTION)

    assert result == f"[English] {BRANCH_QUESTION}"
    assert len(fake.calls) == calls_after_setup


async def test_대본에_없는_발화는_즉석에서_번역한다(monkeypatch):
    fake = _install_translator(monkeypatch)
    session = Session(title="P01", interpretation_language="en", questions=_questions())
    improvised = "조금 더 구체적으로 들려주시겠어요?"

    result = await translate_assistant_text(session, improvised)

    assert result == f"[English] {improvised}"
    assert fake.calls[-1][0] == improvised


async def test_통역_언어가_한국어면_AI_발화도_번역하지_않는다(monkeypatch):
    fake = _install_translator(monkeypatch)
    session = Session(title="P01", interpretation_language="ko", questions=_questions())

    assert await translate_assistant_text(session, "질문입니다") is None
    assert fake.calls == []


def test_AI_질문_턴에_번역이_함께_기록된다(client, monkeypatch):
    """참관자 대시보드·기록 다운로드·웹 뷰어가 모두 text_en 을 읽는다."""
    _install_translator(monkeypatch)

    session_id = _create_session(client)["id"]

    with client.websocket_connect(f"/ws/interview/{session_id}") as interviewee:
        interviewee.receive_json()
        client.post(f"/api/sessions/{session_id}/start")
        interviewee.receive_json()
        interviewee.send_json({"type": "utterance", "text": "안녕하세요."})
        interviewee.receive_json()

    turns = client.get(f"/api/sessions/{session_id}/transcript").json()
    assistant_turns = [turn for turn in turns if turn["speaker"] == "assistant"]

    assert assistant_turns
    assert all(turn["text_en"] for turn in assistant_turns)
    assert assistant_turns[0]["text_en"].startswith("[English]")


def test_번역된_AI_질문이_기록_문서에도_들어간다(client, monkeypatch):
    import io

    from docx import Document

    _install_translator(monkeypatch)
    session_id = _create_session(client)["id"]

    with client.websocket_connect(f"/ws/interview/{session_id}") as interviewee:
        interviewee.receive_json()
        client.post(f"/api/sessions/{session_id}/start")
        interviewee.receive_json()
        interviewee.send_json({"type": "utterance", "text": "안녕하세요."})
        interviewee.receive_json()

    response = client.get(f"/api/sessions/{session_id}/transcript/download")
    document = Document(io.BytesIO(response.content))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)

    assert "(EN) [English]" in text


# =========================================================
# 오프닝 인사 기록
# =========================================================

def test_오프닝_인사가_진행_상황에_기록된다(client):
    """응답자 화면이 발화한 인사를 백엔드가 AI 진행자 턴으로 남겨야 한다."""
    session_id = _create_session(client, language="ko")["id"]
    intro = "안녕하세요! 저는 오늘 대화를 진행할 AI 모더레이터입니다."

    with client.websocket_connect(f"/ws/observer/{session_id}") as observer:
        assert observer.receive_json()["type"] == "session.snapshot"

        with client.websocket_connect(f"/ws/interview/{session_id}") as interviewee:
            interviewee.receive_json()
            assert observer.receive_json()["type"] == "interviewee.connected"
            client.post(f"/api/sessions/{session_id}/start")
            interviewee.receive_json()
            observer.receive_json()

            interviewee.send_json({"type": "intro.spoken", "text": intro})

            # 참관자에게 실시간으로 전달되어야 한다
            appended = observer.receive_json()

    assert appended["type"] == "transcript.append"
    assert appended["turn"]["speaker"] == "assistant"
    assert appended["turn"]["text"] == intro

    turns = client.get(f"/api/sessions/{session_id}/transcript").json()
    assert turns[0]["speaker"] == "assistant"
    assert turns[0]["text"] == intro


def test_오프닝_인사는_중복_기록되지_않는다(client):
    """재연결 등으로 같은 인사가 두 번 들어와도 한 번만 남아야 한다."""
    session_id = _create_session(client, language="ko")["id"]
    intro = "안녕하세요! AI 모더레이터입니다."

    with client.websocket_connect(f"/ws/interview/{session_id}") as interviewee:
        interviewee.receive_json()
        client.post(f"/api/sessions/{session_id}/start")
        interviewee.receive_json()
        interviewee.send_json({"type": "intro.spoken", "text": intro})
        interviewee.send_json({"type": "intro.spoken", "text": intro})
        # 두 번째가 처리될 시간을 주기 위해 왕복 한 번
        interviewee.send_json({"type": "utterance", "text": "네 안녕하세요."})
        interviewee.receive_json()

    turns = client.get(f"/api/sessions/{session_id}/transcript").json()
    intro_turns = [turn for turn in turns if turn["text"] == intro]
    assert len(intro_turns) == 1


def test_빈_인사는_무시한다(client):
    session_id = _create_session(client, language="ko")["id"]

    with client.websocket_connect(f"/ws/interview/{session_id}") as interviewee:
        interviewee.receive_json()
        client.post(f"/api/sessions/{session_id}/start")
        interviewee.receive_json()
        interviewee.send_json({"type": "intro.spoken", "text": "   "})
        interviewee.send_json({"type": "utterance", "text": "안녕하세요."})
        interviewee.receive_json()

    turns = client.get(f"/api/sessions/{session_id}/transcript").json()
    assert turns[0]["speaker"] == "interviewee"
