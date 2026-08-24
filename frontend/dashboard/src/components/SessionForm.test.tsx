import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import SessionForm, { NewSessionView, ProjectAccessIdCard } from "./SessionForm";

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

it("shows the PM-created Client Access ID with a copy action", () => {
  const markup = renderToStaticMarkup(
    <ProjectAccessIdCard accessId="PRJ-A7F3K9M2Q8ZX" />,
  );

  expect(markup).toContain("Client Access ID");
  expect(markup).toContain("PRJ-A7F3K9M2Q8ZX");
  expect(markup).toContain("ID 복사");
});

it("keeps the selected project's Client Access ID visible while PM creates a session", () => {
  const markup = renderToStaticMarkup(
    <NewSessionView
      projects={[{
        id: "project-1",
        title: "Laptop study",
        access_id: "PRJ-A7F3K9M2Q8ZX",
        research_purpose: "purpose",
        question_script: "1. question",
        questions: [],
        created_at: "2026-08-24T00:00:00Z",
      }]}
      presetProjectId="project-1"
      onCreated={() => undefined}
    />,
  );

  expect(markup).toContain("Client Access ID");
  expect(markup).toContain("PRJ-A7F3K9M2Q8ZX");
});
