# Research results platform design

## Goal

Apply the approved Gromit research-platform HTML design to the React app served at
`http://localhost:5175`. The experience must present multiple research topics,
open each topic on its own results page, provide an interactive Power BI-inspired
view, and make its main artifacts downloadable without a modal.

## Experience

- Use the existing Gromit layout with a black, white, and Apple-blue visual system.
- Add a keyboard-accessible Product menu containing Research Workspace, guide
  upload, interview observation, research results, and a download center.
- Make topic lists vertical and data-driven. Selecting one navigates to
  `/projects/:projectId/results`.
- Let the results dashboard switch between Evidence, research coverage, and
  session status views. The active view changes the chart data and explanatory
  copy.
- Provide a direct Word-compatible report and CSV dataset download on a completed
  project. Files are created in the browser from mock data; no backend request is
  made during this MVP.

## Boundaries

- All changes stay within `frontend/web`.
- `src/mock/` remains the source of research content.
- The production API can later replace the mock data/download adapters; it is not
  called here.
