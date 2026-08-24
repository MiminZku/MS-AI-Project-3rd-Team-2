# Final role-boundary fixes report

## Scope

Only `frontend/web` was changed. The application remains mock-only: no API
calls, browser storage, backend, dashboard, or interviewee changes were made.

## Implemented fixes

- Client project rows, home, projects, download listings, and results now omit
  operational project/session state. Client results retain delivery-safe
  evidence and key-finding metadata only; PM retains owner, update, session,
  processing, and research-gap information.
- Client session rows no longer render completion/scheduled state or completion
  timestamps. They identify approved sessions and their permitted delivery
  artifacts instead.
- Client footer no longer advertises the Power BI dataset. PM still sees it.
- Public/product route pages are lazy-loaded behind a visible in-layout route
  fallback. The login entry no longer contains project fixture identifiers;
  `researchProjects` is emitted as a separate build chunk.
- Results selection initializes to the first permitted session. Client lookup
  uses only the safe catalogue; PM lookup uses the PM catalogue. The PM-only
  `Research operations` session now maps to an existing evidence focus, so its
  selection updates the BI focus.
- PM session fixtures have a truthful `hasTranscript` field. The Full
  transcript badge is emitted only when that field is true.

## TDD evidence

### RED

1. `npm test -- researchSessions TopicList InsightDashboard Footer`
   - Exit 1; 4 test files failed as intended.
   - Failures proved the missing transcript availability check, visible client
     Power BI footer item, client topic operational state/progress, and client
     dashboard status/KPIs.
2. `npm test -- researchInsights`
   - Exit 1; the PM-only `Research operations` mapping was `undefined` rather
     than the existing handoff evidence theme.
3. `npm test -- SessionList`
   - Exit 1; the client session row still rendered `Completed`.

### GREEN

1. `npm test -- researchSessions researchInsights TopicList InsightDashboard Footer`
   - Exit 0; 5 files and 17 tests passed.
2. `npm test -- SessionList researchSessions researchInsights TopicList InsightDashboard Footer`
   - Exit 0; 6 files and 18 tests passed.

## Files changed

- `src/App.tsx`
- `src/components/research/DirectDownloads.tsx`
- `src/components/research/InsightDashboard.tsx`
- `src/components/research/SessionList.tsx`
- `src/components/research/TopicList.tsx`
- `src/layout/Footer.tsx`
- `src/lib/researchSessions.ts`
- `src/mock/pmResearchSessions.ts`
- `src/mock/researchProjects.ts`
- `src/pages/Downloads.tsx`
- `src/pages/Home.tsx`
- `src/pages/Projects.tsx`
- `src/pages/ResearchResults.tsx`
- `src/styles/global.css`
- Tests: `TopicList.test.tsx`, `InsightDashboard.test.tsx`,
  `ResearchResults.test.tsx`, and updated session/footer/insight tests.

## Final verification

- `npm test` — exit 0: 16 test files, 30 tests passed.
- `npm run build` — exit 0: `tsc --noEmit` and Vite production build passed.
  The build emitted `researchProjects-C67vflOT.js` separately. A post-build
  scan of `index-Dbl74IZi.js` for `workflow-discovery`, `feature-validation`,
  and `Research Operations` passed with no matches.
- `git diff --check` — exit 0. Git printed pre-existing line-ending warnings
  for unrelated dirty files, but reported no whitespace errors.

## Remaining mock-security limitation

These role boundaries are rendering and bundle-delivery safeguards, not server
authorization. Role choice lives only in in-memory React context, all fixtures
remain frontend assets once their lazy routes/chunks are requested, and a user
can inspect or fetch those assets. A real backend must enforce authentication,
authorization, and role-filtered data responses before any PM-only data can be
considered protected.

## Correction: shared preview and project summary boundaries

The shared `ResearchHero` preview is now explicitly role-aware. PM receives
`Live workspace`, `Sessions 18 / 20`, and `2 ready`; client receives
delivery-safe workspace, approved-evidence, and delivery-report labels with no
session total, live operational state, or readiness count. The Projects summary
now shows its total-project and ready-project wording only to PM; client sees
`Research delivery` and delivery-safe copy.

### Correction TDD evidence

- RED: `npm test -- Home Projects ResearchHero` exited 1. The new server-render
  tests found `18 / 20` in client home markup and the total-project wording in
  client Projects markup.
- GREEN: `npm test -- Home Projects ResearchHero` exited 0: 3 files and 3
  tests passed. The tests assert client markup excludes `18 / 20`, `Live
  workspace`, `2 ready`, total-project wording, and ready-state wording, while
  PM markup retains those operational indicators.
- Final: `npm test` exited 0 (18 files, 32 tests); `npm run build` exited 0;
  `git diff --check` exited 0 with only pre-existing line-ending warnings.

Correction files: `src/sections/platform/ResearchHero.tsx`,
`src/pages/Projects.tsx`, `src/pages/Home.test.tsx`, and
`src/pages/Projects.test.tsx`.
