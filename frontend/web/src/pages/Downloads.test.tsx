import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { expect, it } from "vitest";
import { RoleProvider } from "../auth/RoleContext";
import Downloads from "./Downloads";

it("keeps analysis-data copy out of the client download center", () => {
  const clientMarkup = renderToStaticMarkup(
    <MemoryRouter><RoleProvider initialRole="client"><Downloads /></RoleProvider></MemoryRouter>,
  );
  const pmMarkup = renderToStaticMarkup(
    <MemoryRouter><RoleProvider initialRole="pm"><Downloads /></RoleProvider></MemoryRouter>,
  );

  expect(clientMarkup).toContain("delivery-ready reports");
  expect(clientMarkup).not.toContain("analysis data");
  expect(pmMarkup).toContain("analysis data");
});
