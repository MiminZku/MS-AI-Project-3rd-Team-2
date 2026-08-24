import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import * as GromitIntroModule from "./GromitIntro";

const GromitIntro = GromitIntroModule.default;

it("renders the Gromit mark and a keyboard-accessible skip action", () => {
  const markup = renderToStaticMarkup(<GromitIntro onComplete={() => undefined} />);

  expect(markup).toContain("GROMIT");
  expect(markup).toContain("인트로 건너뛰기");
  expect(markup).not.toContain("<img");
});

it("keeps the automatic opening visible for a 4.8-second midnight sequence", () => {
  const markup = renderToStaticMarkup(<GromitIntro onComplete={() => undefined} />);
  const introDuration = (GromitIntroModule as { INTRO_DURATION_MS?: number }).INTRO_DURATION_MS;

  expect(introDuration).toBe(4800);
  expect(markup).toContain("gromit-intro__aurora");
  expect(markup).toContain("gromit-intro__starfield");
});
