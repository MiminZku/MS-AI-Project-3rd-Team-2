import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { expect, it } from "vitest";
import { RoleProvider } from "../../auth/RoleContext";
import DownloadCatalog from "./DownloadCatalog";

it("keeps the client catalog limited to the delivery-ready Word report", () => {
  const clientMarkup = renderToStaticMarkup(
    <MemoryRouter><RoleProvider initialRole="client"><DownloadCatalog expanded /></RoleProvider></MemoryRouter>,
  );
  const pmMarkup = renderToStaticMarkup(
    <MemoryRouter><RoleProvider initialRole="pm"><DownloadCatalog expanded /></RoleProvider></MemoryRouter>,
  );

  expect(clientMarkup).toContain("Executive Word report");
  expect(clientMarkup).not.toContain("Power BI dataset");
  expect(clientMarkup).not.toContain("Interview recording");
  expect(pmMarkup).toContain("Full Word report");
  expect(pmMarkup).toContain("Power BI dataset");
});
