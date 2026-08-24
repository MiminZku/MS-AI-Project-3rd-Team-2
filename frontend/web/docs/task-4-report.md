# Task 4 — Session list and role-aware detail screen

## Delivered

- Added `SessionList` below the project BI with status, segment, duration, completed/scheduled time, selected state, and role-permitted artifact badges.
- Added nested session routes at `/projects/:projectId/sessions/:sessionId`.
- Added separate PM and client detail branches. PM receives the full transcript, PM interpretation, recording placeholder, observer controls, and evidence. Client receives only an approved digest, approved quotes, themes, and a safe-artifact panel.
- Role-filtered lookup now gates session URLs. Inaccessible session IDs redirect to that project's results route.

## TDD evidence

Two pure role-access helpers were developed red-green in `src/lib/researchSessions.test.ts`:

1. `getPermittedSessionArtifacts` initially failed with `TypeError: getPermittedSessionArtifacts is not a function`; it now verifies that client badges contain only approved digest/quotes/themes and never a full transcript, while PM badges include transcript and recording.
2. `getSessionRedirectPath` initially failed with `TypeError: getSessionRedirectPath is not a function`; it now verifies a valid PM operational session URL, a valid client-approved URL, and client redirection for `session-03`.

## Verification

- `npm test -- researchSessions.test.ts` — 5 tests passed.
- `npm test` — 12 tests passed.
- `npm run build` — passed; TypeScript checked cleanly and Vite produced the production bundle.

## Files

- `src/components/research/SessionList.tsx`
- `src/components/research/SessionDetail.tsx`
- `src/pages/ResearchSession.tsx`
- `src/pages/ResearchResults.tsx`
- `src/App.tsx`
- `src/lib/researchSessions.ts`
- `src/lib/researchSessions.test.ts`
- `src/styles/global.css`

## Concern

The local Vite server returned HTTP 200, but this environment did not expose an interactive browser surface for click-through visual testing. Route behavior is covered by the focused role-policy unit test; manual UI review in a browser remains recommended.

## Review fixes

- Separated the synchronously imported client-safe session catalogue from PM-only notes and operational sessions. PM session data is now loaded through a dynamic import only when the role is PM.
- Moved the PM transcript/detail UI into `PmSessionDetail.tsx`, dynamically imported only from the PM role branch. The client detail module has no raw transcript import or PM control import.
- Added session-specific PM transcript lookup: only `session-01` has the current mock transcript; scheduled `session-04` renders the no-transcript state.
- Client delivery now renders every approved quote. Client session artifact badges use a neutral tag icon rather than a lock.

### RED/GREEN evidence

1. `SessionDetail.test.tsx` failed first because `ClientSessionDetail` was not exported. After the client-safe component was exposed and quotes were mapped, it passed while proving both approved quotes are present and PM labels/raw transcript text are absent from server-rendered client markup.
2. `pmSessionTranscripts.test.ts` failed first because the PM-only transcript module did not exist. After adding the session-keyed PM fixture, it passed by finding six turns for `session-01` and no transcript for `session-04`.

### Current verification

- Focused suite: 3 files, 7 tests passed (`SessionDetail`, PM transcript fixture, and session access).
- Production build passed. Vite emitted separate `pmResearchSessions` and `PmSessionDetail` chunks, confirming those modules are not part of the initial client bundle.

### Authorization boundary

This is still a mock, front-end-only workspace. Dynamic imports and client-side route filtering reduce initial-load exposure and prevent the client branch from requesting PM modules, but actual authorization of transcript and operational research data requires server-side authentication and authorization enforcement before production use.

## Services route follow-up

- `/services` is now wrapped in `RequirePmRole`, which redirects any non-PM role to `/projects`.
- `Services` is loaded with `React.lazy`, so its `ReportAnalysis` and raw transcript dependency are absent from the initial application chunk.
- Client navigation no longer renders the Services entry; PM navigation retains it.

### RED/GREEN evidence

`RequireRole.test.tsx` first failed because `RequirePmRole` was missing. After introducing the generic PM guard, the focused test passed: client-rendered PM-only content is denied and the same content remains available to PMs.

### Current verification

- Focused guard test: 3 tests passed.
- Full suite: 6 files, 15 tests passed.
- Production build passed. Vite emitted separate `Services`, `PmSessionDetail`, and `transcript` chunks; the initial `index` bundle no longer contains the Services transcript path.

## Footer and home CTA follow-up

- The footer’s interview/observer link now renders only for PM roles; client footer markup contains no `/services` destination.
- The current home hero already uses client-safe CTAs (`/projects` and `/downloads`), so it required no change.

### RED/GREEN evidence

`Footer.test.tsx` first failed because a client footer render contained `href="/services"`. After gating the footer link with `useRole`, the same test passed: client markup has no Services destination and PM markup retains it.

### Current verification

- Focused footer test: 1 test passed.
- Full suite: 7 files, 16 tests passed.
- Production build passed.

## Hero CTA correction

- PM users now receive the hero’s operational CTA to `/services` ("인터뷰 운영 보기").
- Client users receive the delivery-safe CTA to `/downloads` ("승인된 산출물 보기") and no `/services` destination.

### RED/GREEN evidence

`ResearchHero.test.tsx` was introduced with the required role matrix and failed RED because PM markup lacked `href="/services"`. After the hero adopted `useRole` and rendered the CTA conditionally, it passed GREEN: client markup contains `/downloads` but no `/services`, while PM markup contains `/services`.

### Current verification

- Focused hero test: 1 test passed.
- Full suite: 8 files, 17 tests passed.
- Production build passed.
