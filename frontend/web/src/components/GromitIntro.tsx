import { useCallback, useEffect, useRef } from "react";

const INTRO_STORAGE_KEY = "gromit.landing-intro.seen";
export const INTRO_DURATION_MS = 4800;

type GromitIntroProps = {
  onComplete: () => void;
};

function hasSeenIntro(): boolean {
  if (typeof window === "undefined") {
    return false;
  }

  try {
    return window.sessionStorage.getItem(INTRO_STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

export default function GromitIntro({ onComplete }: GromitIntroProps) {
  const didComplete = useRef(false);

  const complete = useCallback(() => {
    if (didComplete.current) {
      return;
    }

    didComplete.current = true;

    if (typeof window !== "undefined") {
      try {
        window.sessionStorage.setItem(INTRO_STORAGE_KEY, "true");
      } catch {
        // Storage can be disabled in a private browser context. The current visit still continues.
      }
    }

    onComplete();
  }, [onComplete]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return undefined;
    }

    const prefersReducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (hasSeenIntro() || prefersReducedMotion) {
      complete();
      return undefined;
    }

    const timer = window.setTimeout(complete, INTRO_DURATION_MS);
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        complete();
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [complete]);

  return (
    <section
      className="gromit-intro"
      aria-label="Gromit landing introduction"
      onClick={complete}
    >
      <div className="gromit-intro__aurora" aria-hidden="true" />
      <div className="gromit-intro__starfield" aria-hidden="true" />
      <div className="gromit-intro__glow" aria-hidden="true" />
      <div className="gromit-intro__content">
        <p className="gromit-intro__eyebrow">AI QUALITATIVE RESEARCH PLATFORM</p>
        <h1 className="gromit-intro__wordmark" aria-label="GROMIT">GROMIT</h1>
        <p className="gromit-intro__tagline">Research, heard clearly.</p>
      </div>
      <button
        className="gromit-intro__skip"
        type="button"
        onClick={(event) => {
          event.stopPropagation();
          complete();
        }}
      >
        인트로 건너뛰기
      </button>
      <p className="gromit-intro__hint" aria-hidden="true">CLICK ANYWHERE TO CONTINUE</p>
    </section>
  );
}
