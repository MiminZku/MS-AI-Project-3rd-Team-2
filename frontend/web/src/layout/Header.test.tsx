import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { expect, it } from "vitest";
import { RoleProvider } from "../auth/RoleContext";
import Header from "./Header";

it("labels the active workspace role and exposes an accessible logout action", () => {
  const clientMarkup = renderToStaticMarkup(
    <MemoryRouter><RoleProvider initialRole="client"><Header /></RoleProvider></MemoryRouter>,
  );
  const pmMarkup = renderToStaticMarkup(
    <MemoryRouter><RoleProvider initialRole="pm"><Header /></RoleProvider></MemoryRouter>,
  );

  expect(clientMarkup).toContain("클라이언트 전달용");
  expect(pmMarkup).toContain("PM 운영");
  expect(clientMarkup).toContain('aria-label="로그아웃"');
  expect(pmMarkup).toContain('aria-label="로그아웃"');
});
