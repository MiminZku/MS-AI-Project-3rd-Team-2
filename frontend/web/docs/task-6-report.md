# Task 6 report — role-aware downloads and visual polish

## Delivered

- `DirectDownloads` now requires `role` and uses `rolePermissions(role).viewPowerBiDataset` before it creates or renders a BI/CSV artifact.
  - PM: **Full Word report** plus **Power BI dataset**.
  - Client: **Executive Word report** only; no CSV, Power BI control, or restricted-artifact hint is rendered.
- `DownloadCatalog` now reads the active role and presents only deliverable artifacts. It no longer advertises unavailable individual reports or interview recordings.
- `ResearchResults` passes the authenticated role into `DirectDownloads`.
- The header shows the compact **PM 운영** or **클라이언트 전달용** badge. Its logout controls call `logout()` and navigate to `/login`; the client primary action leads to delivery reports rather than research creation.
- Added responsive header, artifact, catalog focus/availability, and client single-download styling while retaining the existing black, white, and Apple-blue palette.

## RED / GREEN evidence

### Direct download policy

1. **RED** — added `DirectDownloads.test.tsx`, then ran:

   ```text
   npm test -- DirectDownloads.test.tsx
   FAIL: expected client markup to contain "Executive Word report"
   ```

   The previous component had no `role` prop and rendered the Power BI dataset for every viewer.

2. **GREEN** — implemented the permission guard and ran:

   ```text
   npm test -- DirectDownloads.test.tsx
   Test Files  1 passed (1)
   Tests       1 passed (1)
   ```

### Catalog policy

1. **RED** — added `DownloadCatalog.test.tsx`, then ran:

   ```text
   npm test -- DownloadCatalog.test.tsx
   FAIL: expected client markup to contain "Executive Word report"
   ```

   The catalog still showed its shared report, CSV, individual-report, and recording rows.

2. **GREEN** — made the catalog role-aware and ran:

   ```text
   npm test -- DownloadCatalog.test.tsx DirectDownloads.test.tsx
   Test Files  2 passed (2)
   Tests       2 passed (2)
   ```

### Header role surface

1. **RED** — added `Header.test.tsx`, then ran:

   ```text
   npm test -- Header.test.tsx
   FAIL: expected client markup to contain "클라이언트 전달용"
   ```

2. **GREEN** — added role badges and accessible logout buttons, then ran:

   ```text
   npm test -- Header.test.tsx DownloadCatalog.test.tsx DirectDownloads.test.tsx
   Test Files  3 passed (3)
   Tests       3 passed (3)
   ```

## Full verification

Ran from `frontend/web` after all source and style edits:

```text
npm test
Test Files  12 passed (12)
Tests       23 passed (23)

npm run build
tsc --noEmit && vite build
✓ built in 4.61s
```

`App.tsx` declares the requested SPA routes: `/login`, `/projects`, `/projects/:projectId/results`, and `/projects/:projectId/sessions/:sessionId`.

## Route-check note

I attempted to start a temporary Vite server on port 5176 and request all four routes. The environment command policy rejected the `Start-Process` call before the server started, so HTTP route smoke requests could not be run here. The production build and route declarations above passed; browser route smoke testing remains the only unexecuted check.

## Review remediation — artifact payload and tablet header

### Role-aware Word payload

1. **RED** — changed the existing research-insight test to require distinct PM and client payloads, then ran:

   ```text
   npm test -- researchInsights.test.ts
   FAIL: expected "...-research-report.doc" to match /-internal-research-report\.doc$/
   ```

2. **GREEN** — `makeWordReport(project, role)` now returns an internal PM report or a delivery-safe client report. The focused check passed:

   ```text
   npm test -- researchInsights.test.ts DirectDownloads.test.tsx
   Test Files  2 passed (2)
   Tests       7 passed (7)
   ```

   The test verifies distinct filenames and content. The client payload excludes the project owner, `Session operations`, `Internal evidence detail`, and the detailed evidence summary, while the PM payload includes its internal context.

### Download-center copy

1. **RED** — added `Downloads.test.tsx`, then ran:

   ```text
   npm test -- Downloads.test.tsx
   FAIL: expected client markup to contain "delivery-ready reports"
   ```

2. **GREEN** — the page reads the active role. PM copy states that reports and analysis data can be saved; client copy states only that delivery-ready reports can be saved:

   ```text
   npm test -- Downloads.test.tsx DownloadCatalog.test.tsx
   Test Files  3 passed (3)
   Tests       3 passed (3)
   ```

### Tablet header

At 769–900px, the desktop navigation/actions are hidden and the existing hamburger menu is explicitly enabled. This prevents the role badge, navigation, CTA, and logout controls from crowding a single header row while retaining the same mobile-menu interaction.

### Final verification

```text
npm test
Test Files  13 passed (13)
Tests       24 passed (24)

npm run build
tsc --noEmit && vite build
✓ built in 6.41s
```
