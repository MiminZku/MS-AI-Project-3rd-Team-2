import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { expect, it } from "vitest";
import { RoleProvider } from "../auth/RoleContext";
import Footer from "./Footer";

it("does not expose the PM-only services destination to clients", () => {
  const clientMarkup = renderToStaticMarkup(
    <MemoryRouter><RoleProvider initialRole="client"><Footer /></RoleProvider></MemoryRouter>,
  );
  const pmMarkup = renderToStaticMarkup(
    <MemoryRouter><RoleProvider initialRole="pm"><Footer /></RoleProvider></MemoryRouter>,
  );

  expect(clientMarkup).not.toContain('href="/services"');
  expect(clientMarkup).not.toContain("Power BI");
  expect(pmMarkup).toContain('href="/services"');
  expect(pmMarkup).toContain("Power BI");
});
