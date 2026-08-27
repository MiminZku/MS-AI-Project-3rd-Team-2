"""번역 백필 스크립트 회귀 테스트.

질문 번역은 세션 생성 시점에만 채워지므로, 그 기능이 배포되기 전에 만들어진
세션은 번역이 비어 있고 자동으로 채워지지 않는다. 이 스크립트가 그 공백을 메운다.

핵심 요구사항:
  - 여러 번 돌려도 안전할 것 (이미 채워진 항목은 건너뛴다)
  - --apply 없이는 DB를 건드리지 않을 것
  - 통역 언어가 원문과 같으면 번역 호출 자체를 하지 않을 것
"""

from app.schemas.session import QuestionNode, Session, Turn
from app.services import store as store_module
from app.services.ai import translation as translation_module
from app.scripts.backfill_translations import backfill

MAIN_QUESTION = "요즘 어떤 AI 도구를 쓰시나요?"
BRANCH_QUESTION = "클로드를 고른 이유가 있을까요?"


class _FakeTranslator:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def translate(self, text: str, *, target_language: str) -> str:
        self.calls.append(text)
        return f"[{target_language}] {text}"


def _install_translator(monkeypatch) -> _FakeTranslator:
    fake = _FakeTranslator()
    monkeypatch.setattr(translation_module, "_translator", fake)
    monkeypatch.setattr(translation_module, "_initialized", True)
    return fake


def _fresh_store(monkeypatch) -> store_module.InMemoryStore:
    store = store_module.InMemoryStore()
    monkeypatch.setattr(store_module, "_store", store)
    return store


def _session(*, language: str = "en", translated: bool = False) -> Session:
    question = QuestionNode(
        id="q1",
        order=1,
        text=MAIN_QUESTION,
        branches={"클로드": BRANCH_QUESTION},
    )
    if translated:
        question.text_translated = "already translated"
        question.branches_translated = {"클로드": "already translated branch"}

    return Session(
        study_id="study_1",
        title="P01",
        status="ended",
        interpretation_language=language,
        questions=[question],
    )


async def _seed(store, session: Session, turns: list[Turn] | None = None) -> None:
    await store.save_session(session)
    for turn in turns or []:
        await store.append_turn(session.id, turn)


# =========================================================
# 질문 트리 백필
# =========================================================

async def test_비어있는_질문_번역을_채운다(monkeypatch):
    store = _fresh_store(monkeypatch)
    _install_translator(monkeypatch)
    session = _session()
    await _seed(store, session)

    counter = await backfill(apply=True, project_id=None, do_questions=True, do_turns=False)

    assert counter.questions_filled == 1
    assert counter.branches_filled == 1
    assert counter.sessions_changed == 1

    stored = await store.get_session(session.id)
    assert stored.questions[0].text_translated == f"[English] {MAIN_QUESTION}"
    assert stored.questions[0].branches_translated["클로드"] == f"[English] {BRANCH_QUESTION}"


async def test_이미_번역된_항목은_건너뛴다(monkeypatch):
    """여러 번 돌려도 중복 번역으로 비용이 새지 않아야 한다."""
    store = _fresh_store(monkeypatch)
    fake = _install_translator(monkeypatch)
    await _seed(store, _session(translated=True))

    counter = await backfill(apply=True, project_id=None, do_questions=True, do_turns=False)

    assert fake.calls == []
    assert counter.questions_filled == 0
    assert counter.branches_filled == 0


async def test_통역_언어가_원문과_같으면_건드리지_않는다(monkeypatch):
    store = _fresh_store(monkeypatch)
    fake = _install_translator(monkeypatch)
    await _seed(store, _session(language="ko"))

    counter = await backfill(apply=True, project_id=None, do_questions=True, do_turns=False)

    assert fake.calls == []
    assert counter.sessions_scanned == 1
    assert counter.sessions_changed == 0


async def test_미리보기_모드는_저장하지_않는다(monkeypatch):
    store = _fresh_store(monkeypatch)
    _install_translator(monkeypatch)
    session = _session()
    await _seed(store, session)

    counter = await backfill(apply=False, project_id=None, do_questions=True, do_turns=False)

    # 무엇이 바뀔지는 알려주되
    assert counter.questions_filled == 1
    # DB는 그대로여야 한다
    stored = await store.get_session(session.id)
    assert stored.questions[0].text_translated is None


# =========================================================
# 인터뷰 기록 백필
# =========================================================

async def test_AI_발화_기록에_번역을_채운다(monkeypatch):
    store = _fresh_store(monkeypatch)
    _install_translator(monkeypatch)
    session = _session()
    await _seed(
        store,
        session,
        turns=[
            Turn(index=0, speaker="assistant", text=MAIN_QUESTION),
            Turn(index=1, speaker="interviewee", text="클로드 씁니다."),
        ],
    )

    counter = await backfill(apply=True, project_id=None, do_questions=False, do_turns=True)

    assert counter.turns_filled == 1

    turns = await store.get_transcript(session.id)
    assert turns[0].text_en == f"[English] {MAIN_QUESTION}"
    # 응답자 발화는 건드리지 않는다 (실시간 통역 담당)
    assert turns[1].text_en is None


async def test_이미_번역된_발화는_다시_번역하지_않는다(monkeypatch):
    store = _fresh_store(monkeypatch)
    fake = _install_translator(monkeypatch)
    session = _session()
    await _seed(
        store,
        session,
        turns=[Turn(index=0, speaker="assistant", text=MAIN_QUESTION, text_en="이미 있음")],
    )

    counter = await backfill(apply=True, project_id=None, do_questions=False, do_turns=True)

    assert fake.calls == []
    assert counter.turns_filled == 0
    turns = await store.get_transcript(session.id)
    assert turns[0].text_en == "이미 있음"


async def test_기록_미리보기는_저장하지_않는다(monkeypatch):
    store = _fresh_store(monkeypatch)
    _install_translator(monkeypatch)
    session = _session()
    await _seed(store, session, turns=[Turn(index=0, speaker="assistant", text=MAIN_QUESTION)])

    await backfill(apply=False, project_id=None, do_questions=False, do_turns=True)

    turns = await store.get_transcript(session.id)
    assert turns[0].text_en is None


# =========================================================
# 범위 지정
# =========================================================

async def test_프로젝트를_지정하면_그_프로젝트만_처리한다(monkeypatch):
    store = _fresh_store(monkeypatch)
    _install_translator(monkeypatch)

    mine = _session()
    mine.study_id = "study_mine"
    other = _session()
    other.study_id = "study_other"
    await _seed(store, mine)
    await _seed(store, other)

    await backfill(apply=True, project_id="study_mine", do_questions=True, do_turns=False)

    assert (await store.get_session(mine.id)).questions[0].text_translated
    assert (await store.get_session(other.id)).questions[0].text_translated is None


# =========================================================
# 저장소 지원
# =========================================================

async def test_전사_교체가_전체를_갈아끼운다(monkeypatch):
    """백필이 기대는 replace_transcript 동작 확인."""
    store = _fresh_store(monkeypatch)
    await store.append_turn("ses_1", Turn(index=0, speaker="assistant", text="이전"))

    await store.replace_transcript(
        "ses_1",
        [Turn(index=0, speaker="assistant", text="이전", text_en="새로 채움")],
    )

    turns = await store.get_transcript("ses_1")
    assert len(turns) == 1
    assert turns[0].text_en == "새로 채움"


# =========================================================
# 번역 실패 시 불필요한 저장 방지 (실측 회귀)
# =========================================================

async def test_번역이_모두_실패하면_세션을_다시_저장하지_않는다(monkeypatch):
    """실측 회귀: 번역 API 인증 오류(401)로 전부 실패했는데도 세션 20건이
    변경 없이 다시 저장(no-op upsert)됐다. changed 플래그가 번역 성공 여부와
    무관하게 True로 켜져 있었기 때문이다."""
    store = _fresh_store(monkeypatch)
    session = _session()
    await _seed(store, session)

    class _AlwaysFailingTranslator:
        async def translate(self, text: str, *, target_language: str) -> str:
            raise RuntimeError("401 Unauthorized")

    monkeypatch.setattr(translation_module, "_translator", _AlwaysFailingTranslator())
    monkeypatch.setattr(translation_module, "_initialized", True)

    saved_sessions: list[Session] = []
    original_save = store.save_session

    async def spy_save_session(target_session: Session) -> None:
        saved_sessions.append(target_session)
        await original_save(target_session)

    monkeypatch.setattr(store, "save_session", spy_save_session)

    counter = await backfill(apply=True, project_id=None, do_questions=True, do_turns=False)

    assert counter.failures == 2  # 메인 질문 1 + 파생질문 1
    assert counter.questions_filled == 0
    assert counter.branches_filled == 0
    assert counter.sessions_changed == 0
    # 아무것도 못 채웠으면 저장할 이유가 없다
    assert saved_sessions == []


async def test_일부만_실패해도_저장된_데이터에는_성공한_것만_반영된다(monkeypatch):
    store = _fresh_store(monkeypatch)
    session = _session()
    await _seed(store, session)

    call_count = 0

    class _PartiallyFailingTranslator:
        async def translate(self, text: str, *, target_language: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("일시적 오류")
            return f"[{target_language}] {text}"

    monkeypatch.setattr(translation_module, "_translator", _PartiallyFailingTranslator())
    monkeypatch.setattr(translation_module, "_initialized", True)

    counter = await backfill(apply=True, project_id=None, do_questions=True, do_turns=False)

    assert counter.failures == 1
    assert counter.questions_filled == 0  # 첫 호출(메인 질문)이 실패
    assert counter.branches_filled == 1   # 두 번째 호출(파생질문)은 성공
    assert counter.sessions_changed == 1

    stored = await store.get_session(session.id)
    assert stored.questions[0].text_translated is None
    assert stored.questions[0].branches_translated["클로드"] == f"[English] {BRANCH_QUESTION}"
