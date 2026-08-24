import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ClientSessionDetail } from "./SessionDetail";
import { getResearchSession } from "../../lib/researchSessions";

describe("ClientSessionDetail", () => {
  it("renders every approved quote without privileged session markup", () => {
    const session = getResearchSession("workflow-discovery", "session-01");
    expect(session).toBeDefined();

    const markup = renderToStaticMarkup(<ClientSessionDetail session={session!} />);

    expect(markup).toContain("I need to know who owns the next step");
    expect(markup).toContain("Exceptions are manageable when the reason is visible");
    expect(markup).not.toContain("PM interpretation");
    expect(markup).not.toContain("Recording placeholder");
    expect(markup).not.toContain("Observer controls");
    expect(markup).not.toContain("Full research record");
    expect(markup).not.toContain("Hello! Thank you for participating");
  });
});
