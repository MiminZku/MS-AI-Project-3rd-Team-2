import { describe, expect, it } from "vitest";
import {
  getPermittedSessionArtifacts,
  getPmProjectSessions,
  getPmResearchSession,
  getProjectSessions,
  getResearchSession,
  getSessionRedirectPath,
} from "./researchSessions";

describe("research session lookup", () => {
  it("excludes unapproved and operational sessions from client delivery", async () => {
    expect(await getPmProjectSessions("workflow-discovery")).toHaveLength(4);
    expect(getProjectSessions("workflow-discovery")).toHaveLength(2);
  });

  it("returns a role-filtered session by project and session id", async () => {
    const clientSession = getResearchSession("workflow-discovery", "session-01");

    expect(clientSession?.clientVisible).toBe(true);
    expect(clientSession).not.toHaveProperty("pmNote");
    expect(getResearchSession("workflow-discovery", "session-03")).toBeUndefined();
    expect(await getPmResearchSession("missing-project", "session-01")).toBeUndefined();
  });

  it("retains PM-only notes for PM lookup", async () => {
    expect((await getPmResearchSession("workflow-discovery", "session-01"))?.pmNote).toBeTruthy();
  });

  it("only exposes client-approved artifacts in session list badges", async () => {
    const session = await getPmResearchSession("workflow-discovery", "session-01");

    expect(session).toBeDefined();
    expect(getPermittedSessionArtifacts(session!, "client")).toEqual([
      "Approved digest",
      "Approved quotes",
      "Themes",
    ]);
    expect(getPermittedSessionArtifacts(session!, "client")).not.toContain("Full transcript");
    expect(getPermittedSessionArtifacts(session!, "pm")).toContain("Full transcript");
    expect(getPermittedSessionArtifacts(session!, "pm")).toContain("Recording");
  });

  it("does not label a completed PM session as having a transcript when none is attached", async () => {
    const session = await getPmResearchSession("workflow-discovery", "session-02");

    expect(session).toBeDefined();
    expect(getPermittedSessionArtifacts(session!, "pm")).not.toContain("Full transcript");
  });

  it("resolves a PM-only selection through the PM catalogue without exposing it to client lookup", async () => {
    expect(getResearchSession("workflow-discovery", "session-03")).toBeUndefined();
    expect((await getPmResearchSession("workflow-discovery", "session-03"))?.dashboardTheme).toBe(
      "Research operations",
    );
  });

  it("redirects client session URLs that are not in the safe catalogue", () => {
    expect(getSessionRedirectPath("workflow-discovery", "session-01")).toBeUndefined();
    expect(getSessionRedirectPath("workflow-discovery", "session-03")).toBe(
      "/projects/workflow-discovery/results",
    );
  });
});
