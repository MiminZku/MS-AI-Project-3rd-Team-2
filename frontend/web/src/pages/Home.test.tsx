import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { expect, it } from "vitest";
import { RoleProvider } from "../auth/RoleContext";
import Home from "./Home";

it("keeps the shared home preview delivery-safe for clients while retaining PM operations indicators", () => {
  const clientMarkup = renderToStaticMarkup(
    <MemoryRouter><RoleProvider initialRole="client"><Home /></RoleProvider></MemoryRouter>,
  );
  const pmMarkup = renderToStaticMarkup(
    <MemoryRouter><RoleProvider initialRole="pm"><Home /></RoleProvider></MemoryRouter>,
  );

  expect(clientMarkup).toContain("GROMIT");
  expect(clientMarkup).toContain("인트로 건너뛰기");
  expect(clientMarkup).not.toContain("18 / 20");
  expect(clientMarkup).not.toContain("Live workspace");
  expect(clientMarkup).not.toContain("2 ready");
  expect(pmMarkup).toContain("18 / 20");
  expect(pmMarkup).toContain("Live workspace");
  expect(pmMarkup).toContain("2 ready");
});
