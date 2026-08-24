# Gromit Automatic Landing Intro Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a one-per-browser-session automatic Gromit typography intro before the existing home landing page.

**Architecture:** Keep `Home` as the page composition root and add a focused `GromitIntro` component. The component owns animation completion, session storage, keyboard/click skip behavior, and reduced-motion behavior; CSS owns the visual animation. No route, API, dashboard, or backend changes are needed.

**Tech Stack:** React 19, TypeScript, CSS animations, Vitest, React SSR static rendering.

## Global Constraints

- Make local changes only; do not commit, push, open a PR, or deploy.
- Do not change the existing home content, role behavior, routes, dashboard, or backend.
- Use no image assets or external CDN dependencies.
- Default duration is 2.6 seconds; click, Escape, and reduced-motion skip immediately.

---

### Task 1: Add the testable automatic intro component

**Files:**

- Create: `frontend/web/src/components/GromitIntro.tsx`
- Create: `frontend/web/src/components/GromitIntro.test.tsx`

**Interfaces:**

- Produces: `GromitIntro({ onComplete: () => void }): JSX.Element | null`
- Stores: `gromit.landing-intro.seen` in `sessionStorage` after completion or skip.

- [ ] **Step 1: Write the failing test**

```tsx
it("renders the Gromit mark and a keyboard-accessible skip action", () => {
  const markup = renderToStaticMarkup(<GromitIntro onComplete={() => undefined} />);
  expect(markup).toContain("GROMIT");
  expect(markup).toContain("인트로 건너뛰기");
  expect(markup).not.toContain("<img");
});
```

- [ ] **Step 2: Run the test to verify the expected missing-component failure**

Run: `npm test -- --run src/components/GromitIntro.test.tsx`

Expected: FAIL because `GromitIntro` does not exist.

- [ ] **Step 3: Implement the focused component**

```tsx
const INTRO_STORAGE_KEY = "gromit.landing-intro.seen";

export default function GromitIntro({ onComplete }: { onComplete: () => void }) {
  const complete = useCallback(() => {
    window.sessionStorage.setItem(INTRO_STORAGE_KEY, "true");
    onComplete();
  }, [onComplete]);
  // Start a 2600ms timeout; listen for Escape; expose a button and click-to-skip.
}
```

Use a guarded browser-storage read. Reduced-motion completes on mount without waiting for the timer.

- [ ] **Step 4: Run the focused test to verify it passes**

Run: `npm test -- --run src/components/GromitIntro.test.tsx`

Expected: PASS.

### Task 2: Integrate the intro with the existing Home composition and visual system

**Files:**

- Modify: `frontend/web/src/pages/Home.tsx`
- Modify: `frontend/web/src/pages/Home.test.tsx`
- Modify: `frontend/web/src/styles/global.css`

**Interfaces:**

- Consumes: `GromitIntro` from Task 1.
- Produces: Home renders the current landing unchanged once the intro has completed or has already been seen in the browser session.

- [ ] **Step 1: Write the failing Home integration assertion**

```tsx
expect(markup).toContain("GROMIT");
expect(markup).toContain("지금 읽을 수 있는 조사 주제");
```

- [ ] **Step 2: Run the Home test to confirm the intro assertion fails**

Run: `npm test -- --run src/pages/Home.test.tsx`

Expected: FAIL because Home does not yet render the Gromit intro.

- [ ] **Step 3: Implement the integration and CSS**

```tsx
const [introComplete, setIntroComplete] = useState(() => isIntroSeen());

return (
  <div className="research-home">
    {!introComplete && <GromitIntro onComplete={() => setIntroComplete(true)} />}
    <ResearchHero />
    {/* existing landing sections unchanged */}
  </div>
);
```

Add CSS for the full-viewport overlay, tracked-letter convergence, blue light sweep, body reveal, mobile sizing, focus visibility, and `prefers-reduced-motion` behavior.

- [ ] **Step 4: Run the focused Home/component tests to verify they pass**

Run: `npm test -- --run src/components/GromitIntro.test.tsx src/pages/Home.test.tsx`

Expected: PASS.

### Task 3: Verify the local front-end deliverable

**Files:**

- Test only; no source additions.

- [ ] **Step 1: Run the full web test suite**

Run: `npm test`

Expected: all tests pass.

- [ ] **Step 2: Run the production type check and build**

Run: `npm run build`

Expected: TypeScript completes without errors and Vite produces `dist/`.

- [ ] **Step 3: Check the working tree without Git mutation**

Run: `git diff --check` and `git status --short`

Expected: no whitespace errors; no Git commit, push, PR, or deployment action is performed.
