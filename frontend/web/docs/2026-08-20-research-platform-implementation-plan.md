# Research platform implementation plan

> The user approved the preceding interactive HTML design and requested immediate
> application to the local React host.

## 1. Data and behavior tests

1. Add Vitest and a `test` script in `frontend/web/package.json`.
2. Write failing tests for a typed project lookup and the three dashboard views.
3. Implement the typed mock project catalogue and pure dashboard/download helpers.
4. Add tests for Word-compatible and CSV download payloads.

## 2. Research pages

1. Build reusable project-list, dashboard, and direct-download components.
2. Add a project workspace page, per-project results route, and download-center
   page to `src/App.tsx`.
3. Replace the landing composition with a research-platform hero, topic catalogue,
   capability overview, and download catalogue.

## 3. Navigation and visual system

1. Update the desktop and mobile navigation with a vertical Product menu and a
   download-center entry.
2. Add responsive styles for the dark shell, cards, dashboard controls, bar chart,
   topic list, and direct download area.
3. Use local React icon components only; do not add a CDN.

## 4. Verification

1. Run the new test suite.
2. Run `npm run build`.
3. Inspect the routes and interaction behavior in the local Vite host where
   available, then review the scoped diff.
