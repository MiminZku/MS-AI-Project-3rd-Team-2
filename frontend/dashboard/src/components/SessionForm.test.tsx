import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import SessionForm from "./SessionForm";

it("shows the project creation entry to PMs but not clients", () => {
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: { location: { search: "" } },
  });

  const pmMarkup = renderToStaticMarkup(
    <SessionForm role="pm" onCreated={() => undefined} />,
  );
  const clientMarkup = renderToStaticMarkup(
    <SessionForm role="client" onCreated={() => undefined} />,
  );

  expect(pmMarkup).toContain("새 프로젝트 만들기");
  expect(clientMarkup).not.toContain("새 프로젝트 만들기");
});
