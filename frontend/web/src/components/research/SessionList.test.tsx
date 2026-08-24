import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { expect, it } from "vitest";
import { RoleProvider } from "../../auth/RoleContext";
import SessionList from "./SessionList";

it("keeps selection in place and exposes a separate session detail link", () => {
  const markup = renderToStaticMarkup(
    <MemoryRouter>
      <RoleProvider initialRole="client">
        <SessionList projectId="workflow-discovery" onSelect={() => undefined} />
      </RoleProvider>
    </MemoryRouter>,
  );

  expect(markup).toContain('aria-pressed="true"');
  expect(markup).toContain("세션 상세");
  expect(markup).toContain('href="/projects/workflow-discovery/sessions/session-01"');
  expect(markup).not.toContain("Completed");
});
