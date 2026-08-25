# Project Creation Slot Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep normal PM project creation available when Azure OpenAI Information Slot generation fails.

**Architecture:** `POST /api/projects` continues to validate and parse its question script. It treats Information Slot generation as optional enrichment, matching the existing guide-upload route: a generator exception is logged, an empty slot list is used, and the Project is saved normally.

**Tech Stack:** FastAPI, Pydantic, pytest, Python logging.

## Global Constraints

- Preserve question-script validation: empty/invalid question scripts remain HTTP 400.
- Preserve successful Azure-generated Information Slots unchanged.
- Do not change Project, Session, Project Access ID, interview, report, or frontend data schemas.
- Work locally only; do not commit, push, create a PR, or deploy.

---

### Task 1: Make normal project creation resilient to slot generation failure

**Files:**
- Modify: `backend/tests/test_observer_controlled_session.py`
- Modify: `backend/app/api/routes/studies.py:52-63`

**Interfaces:**
- Consumes: `get_slot_generator().generate(title, research_purpose, question_script, questions)`.
- Produces: `POST /api/projects` returns `201` with `study.information_slots == []` if the generator raises.

- [ ] **Step 1: Write the failing test**

```python
class _FailingSlotGenerator:
    async def generate(self, **_: object) -> list[object]:
        raise RuntimeError("Azure OpenAI unavailable")


def test_project_creation_survives_information_slot_generation_failure(client, monkeypatch):
    from app.api.routes import studies

    monkeypatch.setattr(studies, "get_slot_generator", lambda: _FailingSlotGenerator())

    response = client.post(
        "/api/projects",
        json={
            "title": "Fallback project",
            "research_purpose": "Verify resilient local project creation",
            "question_script": "1. What matters most to you?",
        },
    )

    assert response.status_code == 201
    assert response.json()["study"]["information_slots"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_observer_controlled_session.py::test_project_creation_survives_information_slot_generation_failure -q`

Expected: the `RuntimeError` propagates and the request does not return HTTP 201.

- [ ] **Step 3: Write minimal implementation**

```python
slot_generator = get_slot_generator()
try:
    information_slots = await slot_generator.generate(
        title=payload.title,
        research_purpose=payload.research_purpose,
        question_script=payload.question_script,
        questions=questions,
    )
except Exception as error:
    logger.warning("Information Slot generation skipped: %s", error)
    information_slots = []
```

Add `import logging` and `logger = logging.getLogger(__name__)` once at module scope in `backend/app/api/routes/studies.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_observer_controlled_session.py::test_project_creation_survives_information_slot_generation_failure -q`

Expected: `1 passed`.

- [ ] **Step 5: Run relevant regression tests**

Run: `python -m pytest tests/test_observer_controlled_session.py -q`

Expected: all focused Respondent and project-creation tests pass.

### Task 2: Verify the local PM-to-Respondent flow

**Files:**
- Local-only: `frontend/dashboard/.env.local`
- Local-only: `frontend/interviewee/.env.local`

**Interfaces:**
- Consumes: PM API base URL and Respondent REST/WebSocket base URLs pointed at the healthy local backend.
- Produces: PM project and session creation return a Respondent URL whose initial and running WebSocket messages include the linked project title.

- [ ] **Step 1: Run the full backend suite**

Run: `python -m pytest -q`

Expected: no failures.

- [ ] **Step 2: Run the Respondent production build**

Run: `npm run build` from `frontend/interviewee`.

Expected: TypeScript checks and Vite build complete successfully.

- [ ] **Step 3: Exercise a live local flow**

Create a project with a valid question script, create a session titled `USER-001`, connect to its Respondent WebSocket, start it, and assert at both states:

```python
assert message["session"]["title"] == "USER-001"
assert message["session"]["project_title"] == project_title
```

Expected: the generated Respondent URL loads at `http://localhost:5173/?session=<id>` and its UI uses `project_title`, never `USER-001`, as the visible research title.

- [ ] **Step 4: Preserve local state for the user**

Leave the local PM dashboard, Respondent app, and healthy local API running. Do not commit, push, or deploy.
