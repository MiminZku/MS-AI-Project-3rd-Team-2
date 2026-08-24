import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { researchProjects } from "../../mock/researchProjects";
import InsightDashboard from "./InsightDashboard";

it("keeps operational dashboard status and KPIs out of the client delivery view", () => {
  const project = researchProjects.find((item) => item.id === "feature-validation")!;
  const markup = renderToStaticMarkup(<InsightDashboard project={project} role="client" />);

  expect(markup).not.toContain("processing");
  expect(markup).not.toContain("Completed sessions");
  expect(markup).not.toContain("Research gaps");
  expect(markup).toContain("Evidence");
  expect(markup).toContain("Key findings");
});
