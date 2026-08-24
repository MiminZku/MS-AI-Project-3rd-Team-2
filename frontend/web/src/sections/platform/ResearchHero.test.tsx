import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { expect, it } from "vitest";
import { RoleProvider } from "../../auth/RoleContext";
import ResearchHero from "./ResearchHero";

it("shows a client-safe CTA to clients and the services CTA only to PMs", () => {
  const clientMarkup = renderToStaticMarkup(
    <MemoryRouter><RoleProvider initialRole="client"><ResearchHero /></RoleProvider></MemoryRouter>,
  );
  const pmMarkup = renderToStaticMarkup(
    <MemoryRouter><RoleProvider initialRole="pm"><ResearchHero /></RoleProvider></MemoryRouter>,
  );

  expect(clientMarkup).not.toContain('href="/services"');
  expect(clientMarkup).toContain('href="/downloads"');
  expect(pmMarkup).toContain('href="/services"');
});
