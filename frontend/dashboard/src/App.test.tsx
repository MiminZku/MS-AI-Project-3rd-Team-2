import { renderToStaticMarkup } from "react-dom/server";
import { expect, it, vi } from "vitest";

vi.mock("./components/Monitor", () => ({
  default: () => <div>PM monitor</div>,
}));

import App from "./App";

it("does not expose a Client role through the PM dashboard query string", () => {
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: { location: { search: "?role=client" } },
  });

  const markup = renderToStaticMarkup(<App />);

  expect(markup).toContain("새 프로젝트 만들기");
  expect(markup).not.toContain("클라이언트 모드");
});
