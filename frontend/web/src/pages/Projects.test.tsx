import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { expect, it } from "vitest";
import { RoleProvider } from "../auth/RoleContext";
import { researchProjects } from "../mock/researchProjects";
import Projects from "./Projects";

it("does not render the PM project workspace for client roles", () => {
  const clientMarkup = renderToStaticMarkup(
    <MemoryRouter><RoleProvider initialRole="client"><Projects /></RoleProvider></MemoryRouter>,
  );
  const pmMarkup = renderToStaticMarkup(
    <MemoryRouter><RoleProvider initialRole="pm"><Projects /></RoleProvider></MemoryRouter>,
  );
  const totalProjects = `${researchProjects.length}개 프로젝트`;

  expect(clientMarkup).not.toContain("Research workspace");
  expect(clientMarkup).not.toContain("Research delivery");
  expect(clientMarkup).not.toContain(totalProjects);
  expect(pmMarkup).toContain(totalProjects);
  expect(pmMarkup).toContain("결과 준비됨");
});
