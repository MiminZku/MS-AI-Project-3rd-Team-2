import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { expect, it } from "vitest";
import { RoleProvider } from "../auth/RoleContext";
import Login from "./Login";

it("renders the compact dashboard login form with credential fields", () => {
  const markup = renderToStaticMarkup(
    <MemoryRouter><RoleProvider><Login /></RoleProvider></MemoryRouter>,
  );

  expect(markup).toContain("프로젝트 관리 대시보드 및 현장 운영을 위해 접속합니다.");
  expect(markup).toContain("데모 기간엔 로그인이 되지 않아도 이용할 수 있음");
  expect(markup).toContain('name="email"');
  expect(markup).toContain('name="password"');
  expect(markup).toContain("PM 대시보드 입장");
});
