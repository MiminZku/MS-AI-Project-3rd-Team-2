# Gromit Automatic Landing Intro Design

## Goal

Show a full-screen, high-impact Gromit brand intro before the existing landing page, then transition automatically to the current research landing content.

## Experience

1. A first-time visitor to `/` sees a black full-viewport intro immediately.
2. `G R O M I T` starts widely tracked, sharp, and oversized in the centre of the screen.
3. The letters draw together into `GROMIT`; a restrained blue light sweep and subtitle reinforce the research-workspace identity.
4. At 2.6 seconds, the intro fades and lifts away while the existing `ResearchHero` enters below it.
5. The completion state is written to `sessionStorage`, so refreshes and later navigation in the same browser tab go directly to the existing landing page.
6. Clicking the intro, pressing Escape, or using `prefers-reduced-motion: reduce` skips it immediately without leaving the page.

## Visual Direction

- Apple-like restraint: near-black background, white wordmark, one electric-blue accent, soft radial light rather than photographic assets.
- Typography is the focal point: responsive wordmark, strong tracking animation, no external image/CDN dependency.
- The existing landing content, header, routes, and role-aware sections remain unchanged after the intro disappears.

## Components and State

- Add one `GromitIntro` component responsible only for timing, skip controls, and session completion storage.
- Render it only from `Home`, ahead of the existing page content.
- The component exposes no cross-page state; it reads and writes one session-storage flag only in the browser.

## Accessibility and Failure Handling

- The intro has a visible, keyboard-focusable skip control with an accessible label.
- Escape skips the intro.
- Reduced-motion users never wait for animated content.
- If browser storage is unavailable, the intro still completes locally after its timer; only the per-session skip memory is unavailable.

## Validation

- Static component test verifies the wordmark, skip control, and no external media dependency.
- Home test verifies the existing landing sections remain present.
- Run the full web test suite and production build locally.

## Constraints

- Local changes only; do not commit, push, create a PR, or deploy.
- Do not change backend, dashboard, API, routing, or existing landing content behavior.
