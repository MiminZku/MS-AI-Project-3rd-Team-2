import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import DirectDownloads from "./DirectDownloads";
import { researchProjects } from "../../mock/researchProjects";

const readyProject = researchProjects.find((project) => project.status === "ready");

if (!readyProject) {
  throw new Error("A ready research project is required for download policy tests.");
}

it("renders the BI dataset only for PM operations", () => {
  const clientMarkup = renderToStaticMarkup(
    <DirectDownloads project={readyProject} role="client" />,
  );
  const pmMarkup = renderToStaticMarkup(
    <DirectDownloads project={readyProject} role="pm" />,
  );

  expect(clientMarkup).toContain("Executive Word report");
  expect(clientMarkup).not.toContain("Power BI dataset");
  expect(clientMarkup).not.toContain("CSV");
  expect(pmMarkup).toContain("Full Word report");
  expect(pmMarkup).toContain("Power BI dataset");
});
