import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { expect, it } from "vitest";
import type { ResearchProject } from "../../mock/researchProjects";
import TopicList from "./TopicList";

const processingProject: ResearchProject = {
  id: "delivery-project",
  title: "Delivery project",
  subtitle: "A delivery-safe project summary.",
  description: "",
  status: "processing",
  updatedAt: "2026-08-20",
  owner: "Research operations",
  sessions: { completed: 3, total: 8 },
  coverageScore: 50,
  evidenceCount: 4,
  keyFindingCount: 2,
  researchGaps: 3,
  evidence: [],
  coverage: [],
  sessionStatus: [],
  highlights: [],
};

it("omits operational status and session progress from client topic rows", () => {
  const markup = renderToStaticMarkup(
    <MemoryRouter><TopicList projects={[processingProject]} role="client" /></MemoryRouter>,
  );

  expect(markup).not.toContain("processing");
  expect(markup).not.toContain("3/8");
  expect(markup).toContain("4 Evidence");
});
