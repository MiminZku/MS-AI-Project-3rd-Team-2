# Role-based research workspace design

## Objective

Turn the existing public Gromit research mock into a role-aware product flow:
login is the first screen, then each person enters the same project and session
data with an appropriate PM or client view. The MVP remains entirely in
`frontend/web` and uses mock data only.

## Entry and role model

- `/` redirects to `/login` until a local in-memory role has been chosen.
- The login page has an explicit **PM mode** and **Client mode**. It is a demo
  role selector, not real authentication; credentials are not persisted.
- PM receives the operations workspace: all sessions, their live state, the
  full transcript, observer controls, unredacted evidence, and Word/CSV exports.
- Client receives a delivery workspace: approved sessions, decision-ready
  summary, approved quotes, and a Word-compatible executive report. Raw
  transcript, observer controls, recording, CSV/BI data, and operational
  session states are not rendered.
- A logout action returns to `/login` and clears the active role.

## Session workflow

- A project results page has a vertical session list with status, participant
  segment, duration, completion time, and available artifacts.
- Selecting a session opens `/projects/:projectId/sessions/:sessionId`.
- The PM page shows timeline, full transcript, research notes, evidence,
  recording placeholder, and PM action affordances.
- The client page shows only the approved session digest, approved quotes, key
  themes, and the delivery-safe artifact panel.

## Interactive BI behavior

- Dashboard controls switch entire analysis lenses: Evidence, Coverage, and
  Session state.
- Each horizontal bar is also a control. Selecting it changes the focus card
  to the related evidence summary, supporting quote, linked sessions, and
  recommended action in place. The selected bar is visually distinct and
  keyboard operable.
- Selecting a session synchronizes the dashboard focus with that session's
  evidence where the role is permitted to see it.

## Role-based artifacts

| Artifact | PM | Client |
| --- | --- | --- |
| Executive Word report | direct download | direct download |
| Power BI CSV dataset | direct download | hidden |
| Full transcript | in session detail | hidden |
| Interview recording | session detail placeholder | hidden |
| Individual PDF report | listed as delivery-safe mock | listed as delivery-safe mock |

## Technical boundaries and verification

- New session and permission fixtures live under `src/mock/`.
- React context holds the demo role only for the current tab; no credential,
  session, or role data is written to browser storage.
- Permission derivation and chart-focus mapping are pure helpers covered by
  Vitest. Component behavior is verified through production build and route
  smoke checks.
- No backend, dashboard, or interviewee source is changed and no API is called.
