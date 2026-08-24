# Gromit Midnight Landing Intro Design

## Goal

Refine the public home-page opening sequence into a slower, cinematic midnight presentation without changing the existing home content, routing, roles, login, dashboard, or API behavior.

## Experience

- The intro lasts 4.8 seconds for visitors who have not seen it in the current browser session.
- A near-black, layered night gradient gives the screen visual depth.
- A restrained cobalt aurora and sparse star-like grain sit behind the GROMIT wordmark.
- The wordmark enters as widely tracked, distant type, then eases into its final compact form. A narrow blue glass reflection crosses the letters near the end.
- A final soft blue halo settles as the existing landing page is revealed.
- Clicking the stage, pressing Escape, or using the visible skip button completes the sequence immediately.
- Users who prefer reduced motion and repeat visitors in the same tab skip the animation immediately.

## Scope and Boundaries

- Modify only `frontend/web/src/components/GromitIntro.tsx`, its focused test, and the existing `gromit-intro` CSS rules.
- Keep the existing one-per-tab session storage key and behavior.
- Preserve keyboard accessibility and do not introduce image assets, third-party packages, or remote dependencies.
- Do not change home content, PM/Client behavior, backend code, deployment configuration, or Git state.

## Verification

- Add a testable exported intro duration so the requested 4.8-second timing is explicit.
- Run the focused component and home tests, then the full frontend test suite and production build.
- Run `git diff --check` only; do not commit, push, deploy, or create a pull request.
