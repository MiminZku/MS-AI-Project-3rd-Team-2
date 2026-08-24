import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { expect, it } from "vitest";
import { RoleProvider } from "./RoleContext";
import RequireRole from "./RequireRole";
import RequirePmRole from "./RequirePmRole";

it("withholds guarded content when no role has been selected", () => {
  const markup = renderToStaticMarkup(
    <MemoryRouter>
      <RoleProvider>
        <RequireRole>
          <main>Research workspace</main>
        </RequireRole>
      </RoleProvider>
    </MemoryRouter>,
  );

  expect(markup).not.toContain("Research workspace");
});

it("renders guarded content after a role is selected", () => {
  const markup = renderToStaticMarkup(
    <MemoryRouter>
      <RoleProvider initialRole="pm">
        <RequireRole>
          <main>Research workspace</main>
        </RequireRole>
      </RoleProvider>
    </MemoryRouter>,
  );

  expect(markup).toContain("Research workspace");
});

it("denies PM-only content to client roles while preserving PM access", () => {
  const clientMarkup = renderToStaticMarkup(
    <MemoryRouter>
      <RoleProvider initialRole="client">
        <RequirePmRole><main>Raw interview transcript</main></RequirePmRole>
      </RoleProvider>
    </MemoryRouter>,
  );
  const pmMarkup = renderToStaticMarkup(
    <MemoryRouter>
      <RoleProvider initialRole="pm">
        <RequirePmRole><main>Raw interview transcript</main></RequirePmRole>
      </RoleProvider>
    </MemoryRouter>,
  );

  expect(clientMarkup).not.toContain("Raw interview transcript");
  expect(pmMarkup).toContain("Raw interview transcript");
});
