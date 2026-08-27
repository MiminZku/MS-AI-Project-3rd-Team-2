"""기존 세션에 번역을 소급 채워 넣는 일회성 스크립트.

왜 필요한가
-----------
질문 번역은 **세션을 생성하는 시점에** 한 번 수행해 DB에 저장한다. 그래서 이
기능이 배포되기 전에 만들어진 세션들은 번역이 비어 있고, 코드를 배포해도
자동으로 채워지지 않는다. 그 세션들은 참관자 화면·기록 다운로드·웹 뷰어에서
계속 원문만 보인다.

이 스크립트는 그 공백을 한 번 메운다. 채우는 대상은 두 가지다:

  1. 질문 트리   : QuestionNode.text_translated / branches_translated
  2. 인터뷰 기록 : Turn.text_en 중 AI 진행자(assistant) 발화

이미 값이 있는 항목은 건너뛰므로 여러 번 실행해도 안전하다(멱등).

사용법
------
    # 무엇이 바뀔지만 보고 실제로 쓰지는 않는다 (기본값)
    python -m app.scripts.backfill_translations

    # 실제로 저장한다
    python -m app.scripts.backfill_translations --apply

    # 특정 프로젝트만
    python -m app.scripts.backfill_translations --apply --project study_1486d32b06a8

    # 질문만 / 기록만
    python -m app.scripts.backfill_translations --apply --skip-turns
    python -m app.scripts.backfill_translations --apply --skip-questions

주의
----
- Azure OpenAI 설정(AZURE_OPENAI_*)이 있어야 번역이 동작한다. 없으면 아무것도
  채우지 않고 그 사실만 알려준다.
- 번역 1건당 LLM 호출 1회다. 대상이 많으면 시간과 비용이 든다.
  먼저 dry-run으로 규모를 확인할 것.
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from app.core.config import get_settings
from app.schemas.session import Session
from app.services.ai.translation import (
    SOURCE_LANGUAGE_CODE,
    language_name,
    translate_text,
)
from app.services.store import close_store, get_store

logger = logging.getLogger(__name__)


class Counter:
    """무엇을 얼마나 채웠는지 집계."""

    def __init__(self) -> None:
        self.sessions_scanned = 0
        self.sessions_changed = 0
        self.questions_filled = 0
        self.branches_filled = 0
        self.turns_filled = 0
        self.failures = 0

    def summary(self, *, apply: bool) -> str:
        mode = "저장 완료" if apply else "미리보기 (번역·저장 모두 하지 않음)"
        return (
            f"\n[{mode}]\n"
            f"  검사한 세션      : {self.sessions_scanned}\n"
            f"  변경된 세션      : {self.sessions_changed}\n"
            f"  대상 질문        : {self.questions_filled}\n"
            f"  대상 파생질문    : {self.branches_filled}\n"
            f"  대상 AI 발화 기록: {self.turns_filled}\n"
            f"  번역 실패        : {self.failures}"
        )


def _needs_translation(session: Session) -> bool:
    """통역 언어가 원문과 같으면 번역할 이유가 없다."""
    code = (session.interpretation_language or "").lower()
    return bool(code) and code != SOURCE_LANGUAGE_CODE


async def _translate(text: str, target: str, counter: Counter) -> str | None:
    translated = await translate_text(text, target_language=target)
    if not translated:
        counter.failures += 1
        return None
    return translated


async def _backfill_questions(
    session: Session,
    target: str,
    counter: Counter,
    *,
    apply: bool,
) -> bool:
    """세션의 질문 트리를 채운다. 하나라도 채웠(거나 채울 예정)으면 True.

    미리보기(apply=False)에서는 번역을 호출하지도, 값을 건드리지도 않는다.
    규모만 확인하려다 LLM 비용이 나가거나 데이터가 바뀌면 안 된다.
    """
    changed = False

    for question in session.questions:
        if not question.text_translated:
            counter.questions_filled += 1
            if not apply:
                # 미리보기: 규모만 세고 값은 건드리지 않는다.
                changed = True
            else:
                translated = await _translate(question.text, target, counter)
                if translated:
                    question.text_translated = translated
                    changed = True
                else:
                    counter.questions_filled -= 1

        for condition, branch_text in (question.branches or {}).items():
            if question.branches_translated.get(condition):
                continue
            counter.branches_filled += 1
            if not apply:
                changed = True
            else:
                translated = await _translate(branch_text, target, counter)
                if translated:
                    question.branches_translated[condition] = translated
                    changed = True
                else:
                    counter.branches_filled -= 1

    return changed


async def _backfill_turns(
    session: Session,
    target: str,
    counter: Counter,
    *,
    apply: bool,
) -> None:
    """AI 진행자 발화에 번역을 채운다.

    응답자 발화는 인터뷰 중 실시간 통역으로 이미 채워졌거나, 채워지지 않았다면
    당시 음성이 없으므로 여기서 손대지 않는다.
    """
    store = get_store()
    turns = await store.get_transcript(session.id)

    changed = False
    for turn in turns:
        if turn.speaker != "assistant" or turn.text_en or not turn.text.strip():
            continue

        counter.turns_filled += 1
        if not apply:
            # 미리보기: 규모만 세고 번역도 저장도 하지 않는다.
            continue

        translated = await _translate(turn.text, target, counter)
        if translated:
            turn.text_en = translated
            changed = True
        else:
            counter.turns_filled -= 1

    if changed and apply:
        await store.replace_transcript(session.id, turns)


async def backfill(
    *,
    apply: bool,
    project_id: str | None,
    do_questions: bool,
    do_turns: bool,
) -> Counter:
    store = get_store()
    counter = Counter()

    sessions = await store.list_sessions(project_id)
    print(f"대상 세션 {len(sessions)}건을 검사합니다"
          + (f" (프로젝트 {project_id})" if project_id else ""))

    for session in sessions:
        counter.sessions_scanned += 1

        if not _needs_translation(session):
            continue

        target = language_name(session.interpretation_language)
        changed = False

        if do_questions:
            changed = await _backfill_questions(session, target, counter, apply=apply)

        if changed and apply:
            await store.save_session(session)

        if do_turns:
            await _backfill_turns(session, target, counter, apply=apply)

        if changed:
            counter.sessions_changed += 1
            print(f"  · {session.title or session.id} -> {target}")

    return counter


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="기존 세션의 질문/기록 번역을 소급해서 채웁니다.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="실제로 DB에 저장한다 (기본값은 미리보기)",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="특정 프로젝트(study_id)만 처리",
    )
    parser.add_argument(
        "--skip-questions",
        action="store_true",
        help="질문 트리 번역을 건너뛴다",
    )
    parser.add_argument(
        "--skip-turns",
        action="store_true",
        help="인터뷰 기록(AI 발화) 번역을 건너뛴다",
    )
    return parser.parse_args()


async def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    args = _parse_args()

    if not get_settings().use_azure_openai:
        print(
            "AZURE_OPENAI_* 설정이 없어 번역할 수 없습니다.\n"
            "AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY 를 설정하고 다시 실행하세요."
        )
        return

    if not args.apply:
        print("미리보기 모드입니다. 실제로 저장하려면 --apply 를 붙이세요.\n")

    try:
        counter = await backfill(
            apply=args.apply,
            project_id=args.project,
            do_questions=not args.skip_questions,
            do_turns=not args.skip_turns,
        )
        print(counter.summary(apply=args.apply))
    finally:
        await close_store()


if __name__ == "__main__":
    asyncio.run(main())
