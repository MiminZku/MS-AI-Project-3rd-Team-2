import { describe, expect, it } from "vitest";
import {
  getDashboardView,
  getFocusedEvidence,
  getPermittedDashboardMode,
  getVisualBarWidth,
  getProjectById,
  makePowerBiDataset,
  makeWordReport,
} from "./researchInsights";

describe("research insight helpers", () => {
  it("finds a project from the data-driven catalogue", () => {
    expect(getProjectById("workflow-discovery")?.title).toBe("업무 워크플로우 탐색 조사");
    expect(getProjectById("missing-project")).toBeUndefined();
  });

  it("returns a different visual story for each dashboard control", () => {
    const project = getProjectById("workflow-discovery");

    expect(project).toBeDefined();
    expect(getDashboardView(project!, "evidence").title).toBe("결정을 뒷받침하는 근거");
    expect(getDashboardView(project!, "coverage").title).toBe("조사 범위와 균형");
    expect(getDashboardView(project!, "session").title).toBe("세션 진행 상태");
  });

  it("returns the focused evidence summary and next action for 반복 입력", () => {
    const project = getProjectById("workflow-discovery")!;

    const focused = getFocusedEvidence(project, "evidence", "반복 입력");

    expect(focused.summary).toContain("여러 시스템");
    expect(focused.quote).toContain("세 번 입력");
    expect(focused.sessionCount).toBe(8);
    expect(focused.nextAction).toContain("확인");
  });

  it("normalizes the session lens to evidence for clients", () => {
    expect(getPermittedDashboardMode("client", "session")).toBe("evidence");
    expect(getPermittedDashboardMode("pm", "session")).toBe("session");
  });

  it("maps a PM-only session to a visible evidence focus", () => {
    const project = getProjectById("workflow-discovery")!;

    expect(project.sessionThemeMap?.["Research operations"]).toBe("인수인계");
  });

  it("creates distinct internal and delivery-safe Word report payloads", () => {
    const project = getProjectById("workflow-discovery")!;
    const pmReport = makeWordReport(project, "pm");
    const clientReport = makeWordReport(project, "client");

    expect(pmReport.fileName).toMatch(/-internal-research-report\.doc$/);
    expect(clientReport.fileName).toMatch(/-executive-delivery-report\.doc$/);
    expect(pmReport.contents).toContain("Internal research report");
    expect(pmReport.contents).toContain(project.owner);
    expect(pmReport.contents).toContain("Session operations");
    expect(clientReport.contents).toContain("Executive delivery report");
    expect(clientReport.contents).toContain(project.title);
    expect(clientReport.contents).not.toContain(project.owner);
    expect(clientReport.contents).not.toContain("Session operations");
    expect(clientReport.contents).not.toContain("Internal evidence detail");
    expect(clientReport.contents).not.toContain(project.evidence[0].summary);
    expect(makePowerBiDataset(project).fileName).toMatch(/\.csv$/);
    expect(makePowerBiDataset(project).contents).toContain("segment,evidence_count");
  });

  it("does not draw a visual bar for a zero-valued segment", () => {
    expect(getVisualBarWidth(0, 18)).toBe(0);
    expect(getVisualBarWidth(1, 18)).toBe(12);
    expect(getVisualBarWidth(18, 18)).toBe(100);
  });
});
