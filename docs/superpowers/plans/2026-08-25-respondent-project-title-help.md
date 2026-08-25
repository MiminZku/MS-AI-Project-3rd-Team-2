# Respondent Project Title and Help Modal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep anonymous respondent IDs operationally separate while displaying the linked research project title to respondents, and add reusable troubleshooting help before and during an interview.

**Architecture:** Introduce one backend payload helper that resolves the optional `ResearchStudy.title` from a session's `study_id` and reuses the same respondent-safe state payload for initial WebSocket connection and session start. The respondent app stores the delivered project title separately, uses it only for respondent-facing copy, and owns one UI-only help-modal state that is shared by waiting and running views.

**Tech Stack:** FastAPI, Pydantic, FastAPI TestClient WebSockets, React 18, TypeScript, CSS, Vite.

## Global Constraints

- Make local changes only; do not commit, push, open a pull request, or deploy.
- Preserve `Session.title` as the anonymous respondent identifier and do not change session creation, session ID, question progression, timekeeping, recording, role, route, or access-control behavior.
- Send only the linked project title as optional respondent-facing metadata; never substitute respondent ID, project ID, access ID, or session ID if it is unavailable.
- Reuse a single help-modal component from waiting and running screens; opening it must only update UI state.
- Do not add dependencies or change the interview design tokens in `frontend/interviewee/src/styles.css`.

---

### Task 1: Add a respondent-safe project-title WebSocket payload

**Files:**
- Create: `backend/app/services/respondent_session_state.py`
- Modify: `backend/app/api/ws/interview.py`
- Modify: `backend/app/services/orchestrator.py`
- Modify: `backend/tests/test_observer_controlled_session.py`

**Interfaces:**
- Produces: `async def build_respondent_session_state(session: Session) -> dict[str, object]`.
- Produces: a `session.state.session.project_title` field containing `ResearchStudy.title` or `None`.
- Retains: `session.state.session.title` as the anonymous session/participant ID.

- [ ] **Step 1: Write the failing WebSocket contract tests**

```python
def test_respondent_state_uses_project_title_without_replacing_participant_id(client):
    project = _create_project(client, "Galaxy vs iPhone 구매 의사결정 조사")
    created = client.post("/api/sessions", json={
        "study_id": project["id"],
        "title": "USER-001",
        "duration_minutes": 60,
        "question_script": "",
    }).json()["session"]

    with client.websocket_connect(f"/ws/interview/{created['id']}") as respondent:
        initial = respondent.receive_json()["session"]
        assert initial["title"] == "USER-001"
        assert initial["project_title"] == "Galaxy vs iPhone 구매 의사결정 조사"

        client.post(f"/api/sessions/{created['id']}/start")
        started = respondent.receive_json()["session"]
        assert started["project_title"] == "Galaxy vs iPhone 구매 의사결정 조사"


def test_respondent_state_does_not_fallback_to_participant_id_when_study_is_missing(client):
    session_id = _create_session(client)

    with client.websocket_connect(f"/ws/interview/{session_id}") as respondent:
        state = respondent.receive_json()["session"]
        assert state["title"] == "Observer controlled interview"
        assert state["project_title"] is None
```

- [ ] **Step 2: Run the focused backend tests to verify they fail**

Run: `python -m pytest tests/test_observer_controlled_session.py -q`

Expected: FAIL because the current `session.state` payload does not include `project_title`.

- [ ] **Step 3: Implement one reusable state-payload builder**

```python
async def build_respondent_session_state(session: Session) -> dict[str, object]:
    project_title: str | None = None
    if session.study_id:
        study = await get_store().get_study(session.study_id)
        if study is not None:
            project_title = study.title

    return {
        "id": session.id,
        "title": session.title,
        "project_title": project_title,
        "status": session.status,
        "duration_minutes": session.duration_minutes,
        "questions": [question.model_dump(mode="json") for question in session.questions],
    }
```

Use this helper in the respondent's initial WebSocket `session.state` message and `orchestrator.start_session`. Keep observer payloads and all session persistence unchanged.

- [ ] **Step 4: Run the focused backend tests to verify they pass**

Run: `python -m pytest tests/test_observer_controlled_session.py -q`

Expected: PASS.

### Task 2: Keep project title separate in the respondent application

**Files:**
- Modify: `frontend/interviewee/src/types.ts`
- Modify: `frontend/interviewee/src/App.tsx`
- Modify: `frontend/interviewee/src/components/WaitingScreen.tsx`

**Interfaces:**
- Consumes: `SessionBrief.project_title?: string | null` from Task 1.
- Produces: `projectTitle` React state, used only for respondent-facing project display and opening copy.
- Retains: `sessionId`, `sessionStatus`, questions, timers, recording, and WebSocket behavior.

- [ ] **Step 1: Add the new message-contract field**

```ts
export interface SessionBrief {
  id: string;
  title: string;
  project_title?: string | null;
  status: "created" | "running" | "ended";
}
```

- [ ] **Step 2: Split respondent-facing project title from the anonymous session title**

```tsx
const [projectTitle, setProjectTitle] = useState("");

if (message.type === "session.state") {
  setProjectTitle(message.session.project_title?.trim() ?? "");
}
```

Update the welcome heading, waiting title, running header, and `buildOpeningSpeech` to use `projectTitle`. The fallback must be generic interview copy, never `message.session.title`.

- [ ] **Step 3: Preserve the safe opening-copy fallback**

```tsx
const projectPhrase = projectTitle
  ? `"${projectTitle}"에 참여해 주셔서 감사합니다.`
  : "인터뷰에 참여해 주셔서 감사합니다.";
```

Use the phrase only in the greeting, then preserve the current duration and AI moderator copy.

- [ ] **Step 4: Build the respondent app**

Run: `npm run build`

Working directory: `frontend/interviewee`

Expected: TypeScript and Vite complete successfully.

### Task 3: Add reusable respondent troubleshooting help

**Files:**
- Create: `frontend/interviewee/src/components/InterviewHelpModal.tsx`
- Modify: `frontend/interviewee/src/App.tsx`
- Modify: `frontend/interviewee/src/components/WaitingScreen.tsx`
- Modify: `frontend/interviewee/src/styles.css`

**Interfaces:**
- Produces: `InterviewHelpModal({ isOpen: boolean; onClose: () => void })`.
- Consumes: `isHelpOpen` state from `App`.
- Produces: `WaitingScreen({ title: string; onOpenHelp: () => void })`.

- [ ] **Step 1: Create the shared modal component**

```tsx
interface InterviewHelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function InterviewHelpModal({ isOpen, onClose }: InterviewHelpModalProps) {
  if (!isOpen) return null;
  return <div className="modal-overlay" role="presentation">...</div>;
}
```

Use `role="dialog"`, `aria-modal="true"`, a labelled heading, a visible `X` close button, and an `확인` button. Include exactly the approved user guidance for avatar loading, interruptions, audio output, and microphone recognition. The overlay, close button, and confirm button call only `onClose`.

- [ ] **Step 2: Add waiting-room access to the shared modal**

```tsx
<p className="waiting-help-note">인터뷰 중 화면·아바타·음성에 문제가 생기면 이용 안내를 확인해 주세요.</p>
<button className="waiting-help-button" type="button" onClick={onOpenHelp}>? 이용 안내</button>
```

Render the same `InterviewHelpModal` from `App` while `entryStep === "waiting"`.

- [ ] **Step 3: Add running-stage access without touching session state**

```tsx
const [isHelpOpen, setIsHelpOpen] = useState(false);

<button className="interview-help-trigger" type="button" aria-label="인터뷰 이용 안내 열기" onClick={() => setIsHelpOpen(true)}>?</button>
```

Place the trigger in the existing right header area. Render `InterviewHelpModal` with `onClose={() => setIsHelpOpen(false)}`. Do not place help state in effects or callbacks that update session, question, timer, recorder, or WebSocket state.

- [ ] **Step 4: Add scoped styles without changing design tokens**

```css
.interview-help-dialog { max-height: min(76dvh, 680px); overflow-y: auto; }
.interview-help-trigger { width: 30px; height: 30px; border-radius: 50%; }
.waiting-help-button { background: transparent; border: 1px solid rgba(255,255,255,.18); }
```

Add responsive spacing for the waiting panel and running header. Preserve existing `.modal-overlay` behavior and all root variables.

- [ ] **Step 5: Build the respondent app again**

Run: `npm run build`

Working directory: `frontend/interviewee`

Expected: PASS.

### Task 4: Verify the local integration

**Files:**
- Test only; no source additions.

- [ ] **Step 1: Run the full backend test suite**

Run: `python -m pytest -q`

Working directory: `backend`

Expected: PASS.

- [ ] **Step 2: Run a local respondent build and development server**

Run: `npm run build` and `npm run dev`

Working directory: `frontend/interviewee`

Expected: build passes; local respondent URL is `http://localhost:5173/?session=<session_id>`.

- [ ] **Step 3: Perform the respondent state checks locally**

1. Create two projects with distinct titles and one anonymous respondent session per project.
2. Connect each respondent URL and assert the initial `session.state.project_title` equals only its linked project title.
3. Start each session and assert the subsequent `session.state.project_title` remains its linked title.
4. Open and close the help UI from waiting and running; confirm its local state does not change `session_id`, `sessionStatus`, current question, recorder state, or websocket reference.

- [ ] **Step 4: Confirm the working tree has no whitespace errors**

Run: `git diff --check` and `git status --short`

Expected: no whitespace errors; do not commit, push, deploy, or create a pull request.
