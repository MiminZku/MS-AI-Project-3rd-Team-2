import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { expect, it } from "vitest";
import { RoleProvider } from "../auth/RoleContext";
import ResearchResults from "./ResearchResults";

it("renders only delivery-safe project metadata for a client", () => {
  const markup = renderToStaticMarkup(
    <MemoryRouter initialEntries={["/projects/feature-validation/results"]}>
      <RoleProvider initialRole="client">
        <Routes>
          <Route path="/projects/:projectId/results" element={<ResearchResults />} />
        </Routes>
      </RoleProvider>
    </MemoryRouter>,
  );

  expect(markup).toContain("Evidence");
  expect(markup).toContain("Key findings");
  expect(markup).not.toContain("Session progress");
  expect(markup).not.toContain("Completed sessions");
  expect(markup).not.toContain("Research gaps");
  expect(markup).not.toContain("processing");
});
