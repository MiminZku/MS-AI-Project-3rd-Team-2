# Respondent Project Title and Help Modal Design

## Goal

Show the actual research project title—not the anonymous participant ID or a project identifier—throughout the respondent experience, and provide reusable interview troubleshooting guidance before and during an interview.

## Current Cause

The PM dashboard intentionally stores the anonymous participant ID in `Session.title`. The respondent WebSocket currently publishes that field as `session.state.title`, and the respondent app uses it both as the displayed title and in the AI opening speech. The project title exists on `ResearchStudy.title` but is not sent on the respondent WebSocket channel.

## Data Contract

- Add optional `project_title: str | None` to each respondent `session.state` payload.
- Resolve it from `session.study_id` through the existing store and `ResearchStudy.title`.
- Send this field on initial WebSocket connection and when a session transitions to running.
- Keep `Session.title` unchanged because it remains the anonymous respondent identifier.
- Update the respondent `SessionBrief` type with `project_title?: string | null`.
- Store `projectTitle` separately from the participant/session title. Only `projectTitle` may be rendered in respondent title and welcome copy.
- If the project title is unavailable, render generic interview copy. Never substitute participant ID, project ID, access ID, or session ID.

## Help Experience

- Create a reusable `InterviewHelpModal` component in `frontend/interviewee/src/components`.
- It provides the exact user-facing guidance for avatar loading, video/avatar interruptions, audio output, and microphone recognition.
- The modal has a visible close control and an `확인` action. It closes in place without navigating or altering interview state.
- `WaitingScreen` receives an `onOpenHelp` callback and shows the short prompt plus a `? 이용 안내` button.
- The running stage header receives a compact `?` button that opens the same modal.
- Help-open state belongs to `App` only. It must not update `sessionId`, session status, question state, recording state, or timers.

## Files and Scope

- Backend: `backend/app/api/ws/interview.py`, `backend/app/services/orchestrator.py`, and a focused WebSocket payload test if the current backend test conventions support it.
- Respondent frontend: `App.tsx`, `types.ts`, `WaitingScreen.tsx`, new `InterviewHelpModal.tsx`, and `styles.css`.
- No dashboard, web landing, database schema, session model, session creation, role, routing, or access-control changes.

## Verification

- Add a backend test proving a study-backed session emits `project_title` while retaining its anonymous `title`.
- Build the respondent frontend with `npm run build`.
- Verify through local test fixtures or a local WebSocket session that two sessions associated with different studies display their own project title.
- Verify the help modal opens and closes from waiting and running states without resetting the session or interview state.
- Run `git diff --check`; do not commit, push, deploy, or create a pull request.
