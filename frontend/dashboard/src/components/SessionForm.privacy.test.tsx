import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import type { Session } from "../types";
import { NewSessionView, SessionListRows } from "./SessionForm";

it("uses anonymous participant IDs in the new-session form", () => {
  const markup = renderToStaticMarkup(
    <NewSessionView projects={[]} presetProjectId="" onCreated={() => undefined} />,
  );

  expect(markup).toContain("참가자 ID");
  expect(markup).toContain("INT-001");
  expect(markup).not.toContain("인터뷰 세션 이름");
  expect(markup).not.toContain("김OO");
});

it("uses a server session ID instead of an existing session title", () => {
  const session: Session = {
    id: "session-8f9c-11",
    study_id: "study-1",
    title: "홍길동",
    status: "created",
    duration_minutes: 60,
    questions: [],
    current_question_index: 0,
    created_at: "2026-08-24T00:00:00Z",
    started_at: null,
    ended_at: null,
  };
  const markup = renderToStaticMarkup(
    <SessionListRows sessions={[session]} busy={false} onOpen={() => undefined} />,
  );

  expect(markup).toContain("인터뷰 · session-8f9c-11");
  expect(markup).not.toContain("홍길동");
});
