# Gromit Midnight Landing Intro Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Slow the automatic Gromit landing intro to 4.8 seconds and give it a premium midnight keynote visual treatment.

**Architecture:** Keep the existing `GromitIntro` component as the sole owner of timing, session storage, skip behavior, and reduced-motion behavior. Export the timing constant so its user-visible duration is directly testable. Update only the intro's decorative DOM and its namespaced CSS; the existing Home composition remains unchanged.

**Tech Stack:** React 19, TypeScript, CSS animations, Vitest, React SSR static rendering.

## Global Constraints

- Make local changes only; do not commit, push, open a pull request, or deploy.
- Change only the opening intro component, its focused test, and its existing namespaced CSS.
- Keep the one-per-tab session storage behavior, skip controls, keyboard behavior, and reduced-motion immediate completion.
- Do not add packages, image assets, remote dependencies, routes, API calls, or backend changes.

---

### Task 1: Make the slower cinematic timing explicit and testable

**Files:**
- Modify: `frontend/web/src/components/GromitIntro.tsx`
- Modify: `frontend/web/src/components/GromitIntro.test.tsx`

**Interfaces:**
- Produces: `export const INTRO_DURATION_MS = 4800`.
- Retains: `GromitIntro({ onComplete: () => void })` and the existing `gromit.landing-intro.seen` session storage key.

- [ ] **Step 1: Write the failing timing expectation**

```tsx
import GromitIntro, { INTRO_DURATION_MS } from "./GromitIntro";

it("keeps the automatic opening visible for a 4.8-second cinematic sequence", () => {
  expect(INTRO_DURATION_MS).toBe(4800);
});
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `npm test -- --run src/components/GromitIntro.test.tsx`

Expected: FAIL because `INTRO_DURATION_MS` is either not exported or still equals `2600`.

- [ ] **Step 3: Export the requested timing constant**

```tsx
export const INTRO_DURATION_MS = 4800;
```

Keep the existing timeout as `window.setTimeout(complete, INTRO_DURATION_MS)` so the tested value controls the actual experience.

- [ ] **Step 4: Add the midnight visual-layer markup**

```tsx
<div className="gromit-intro__aurora" aria-hidden="true" />
<div className="gromit-intro__starfield" aria-hidden="true" />
```

Place both before `.gromit-intro__content`; they must remain decorative and inaccessible to screen readers.

- [ ] **Step 5: Run the focused test to verify it passes**

Run: `npm test -- --run src/components/GromitIntro.test.tsx`

Expected: PASS with the existing mark, skip-action, no-image, and new duration assertions.

### Task 2: Apply the midnight keynote visual system

**Files:**
- Modify: `frontend/web/src/styles/global.css`

**Interfaces:**
- Consumes: `.gromit-intro`, `.gromit-intro__aurora`, `.gromit-intro__starfield`, `.gromit-intro__glow`, `.gromit-intro__wordmark`, `.gromit-intro__skip`.
- Produces: A 4.8-second midnight visual sequence that preserves all existing controls and responsive behavior.

- [ ] **Step 1: Replace the generic backdrop with midnight depth**

```css
.gromit-intro {
  background:
    radial-gradient(ellipse 70% 50% at 50% 58%, rgba(17, 82, 180, .20), transparent 70%),
    radial-gradient(ellipse 45% 35% at 14% 15%, rgba(42, 78, 150, .15), transparent 80%),
    linear-gradient(135deg, #020308 0%, #070a14 48%, #010207 100%);
}
```

- [ ] **Step 2: Add restrained aurora, starfield, and glass-reflection animations**

```css
.gromit-intro__aurora { animation: gromit-intro-aurora 4.8s cubic-bezier(.22, .61, .36, 1) both; }
.gromit-intro__starfield { animation: gromit-intro-stars 4.8s ease-out both; }
.gromit-intro::after { animation: gromit-intro-sweep 1.75s cubic-bezier(.45, .01, .19, 1) 2.18s both; }
.gromit-intro__wordmark { animation: gromit-intro-converge 3.75s cubic-bezier(.16, .86, .19, 1) .25s both; }
```

Define all referenced keyframes in the same intro CSS block. Keep motion subtle: no neon palette, no continuous loops, and no animation that obstructs the skip button.

- [ ] **Step 3: Tune the supporting copy and controls for the dark surface**

```css
.gromit-intro__skip { background: rgba(14, 23, 44, .52); backdrop-filter: blur(16px); }
.gromit-intro__tagline { color: rgba(181, 215, 255, .88); }
```

Keep the existing `:focus-visible`, hover, mobile, and `prefers-reduced-motion` rules; extend reduced-motion coverage to the two new decorative layers.

- [ ] **Step 4: Run focused visual-structure tests**

Run: `npm test -- --run src/components/GromitIntro.test.tsx src/pages/Home.test.tsx`

Expected: PASS.

### Task 3: Verify the local deliverable

**Files:**
- Test only; no source additions.

- [ ] **Step 1: Run the complete web test suite**

Run: `npm test`

Expected: all test files and tests pass.

- [ ] **Step 2: Run the production type-check and bundle build**

Run: `npm run build`

Expected: TypeScript exits successfully and Vite writes `dist/`.

- [ ] **Step 3: Confirm the changed tree has no whitespace errors**

Run: `git diff --check` and `git status --short`

Expected: no whitespace errors; no commit, push, pull request, or deployment action is performed.
