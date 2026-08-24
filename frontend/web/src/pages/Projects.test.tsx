import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { expect, it } from "vitest";
import { RoleProvider } from "../auth/RoleContext";
import { researchProjects } from "../mock/researchProjects";
import Projects from "./Projects";

it("keeps project totals and readiness wording in the PM workspace only", () => {
  const clientMarkup = renderToStaticMarkup(
    <MemoryRouter><RoleProvider initialRole="client"><Projects /></RoleProvider></MemoryRouter>,
  );
  const pmMarkup = renderToStaticMarkup(
    <MemoryRouter><RoleProvider initialRole="pm"><Projects /></RoleProvider></MemoryRouter>,
  );
  const totalProjects = `${researchProjects.length}개 프로젝트`;

  expect(clientMarkup).not.toContain(totalProjects);
  expect(clientMarkup).not.toContain("결과 준비됨");
  expect(clientMarkup).toContain("Research delivery");
  expect(pmMarkup).toContain(totalProjects);
  expect(pmMarkup).toContain("결과 준비됨");
});
