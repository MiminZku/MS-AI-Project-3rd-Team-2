import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { expect, it } from "vitest";
import ClientAccess from "./ClientAccess";

it("renders a client-only Project Access ID entry screen without PM navigation", () => {
  const markup = renderToStaticMarkup(
    <MemoryRouter><ClientAccess /></MemoryRouter>,
  );

  expect(markup).toContain("프로젝트 접속");
  expect(markup).toContain("프로젝트 ID를 입력해주세요");
  expect(markup).toContain('name="project-access-id"');
  expect(markup).toContain("프로젝트 접속");
  expect(markup).not.toContain("새 조사 만들기");
  expect(markup).not.toContain("프로젝트 목록");
  expect(markup).not.toContain("관리자");
});
