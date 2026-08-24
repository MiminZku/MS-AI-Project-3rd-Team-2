import {
  researchProjects,
  type DashboardMode,
  type EvidenceItem,
  type FocusedEvidence,
  type ResearchProject,
} from "../mock/researchProjects";
import type { UserRole } from "./roleAccess";

export interface DashboardView {
  title: string;
  description: string;
  totalLabel: string;
  totalValue: string;
  unit: string;
  bars: EvidenceItem[];
}

export interface DownloadPayload {
  fileName: string;
  mimeType: string;
  contents: string;
}

export const getVisualBarWidth = (value: number, largestValue: number): number => {
  if (value <= 0 || largestValue <= 0) return 0;
  return Math.max(12, Math.round((value / largestValue) * 100));
};

export const getProjectById = (projectId: string): ResearchProject | undefined =>
  researchProjects.find((project) => project.id === projectId);

export const getPermittedDashboardMode = (role: UserRole, mode: DashboardMode): DashboardMode =>
  role === "client" && mode === "session" ? "evidence" : mode;

export const getDashboardView = (project: ResearchProject, mode: DashboardMode): DashboardView => {
  if (mode === "coverage") {
    return {
      title: "조사 범위와 균형",
      description: "역할과 사용 맥락별 표본 충족도를 비교합니다. 낮은 막대는 다음 모집 우선순위를 뜻합니다.",
      totalLabel: "Research coverage",
      totalValue: String(project.coverageScore),
      unit: "%",
      bars: project.coverage,
    };
  }

  if (mode === "session") {
    return {
      title: "세션 진행 상태",
      description: "완료된 세션과 남은 운영 작업을 한눈에 확인합니다. 상태별 합계는 전체 세션 수와 같습니다.",
      totalLabel: "Completed sessions",
      totalValue: String(project.sessions.completed),
      unit: ` / ${project.sessions.total}`,
      bars: project.sessionStatus,
    };
  }

  return {
    title: "결정을 뒷받침하는 근거",
    description: "인터뷰 안에서 반복적으로 확인된 행동과 발화를 주제별로 묶었습니다.",
    totalLabel: "Evidence",
    totalValue: String(project.evidenceCount),
    unit: "개",
    bars: project.evidence,
  };
};

export const getFocusedEvidence = (
  project: ResearchProject,
  mode: DashboardMode,
  theme: string,
): FocusedEvidence => {
  const view = getDashboardView(project, mode);
  const bar = view.bars.find((item) => item.theme === theme) ?? view.bars[0];
  const metadata = project.focusedEvidence?.[mode]?.find((item) => item.theme === bar?.theme);

  if (metadata) return metadata;

  return {
    theme: bar?.theme ?? theme,
    summary: bar?.summary ?? "선택한 테마에 대한 공개 근거를 준비 중입니다.",
    quote: project.highlights[0] ?? "공개할 수 있는 인용문을 준비 중입니다.",
    sessionCount: Math.min(project.sessions.completed, Math.max(1, bar?.count ?? 1)),
    nextAction: `${bar?.theme ?? theme} 관련 가설을 다음 검토에서 확인하세요.`,
  };
};

const safeFilePart = (title: string) => title.replace(/\s+/g, "-").replace(/[\\/:*?\"<>|]/g, "");

export const makeWordReport = (project: ResearchProject, role: UserRole): DownloadPayload => {
  const findings = project.highlights.map((finding) => `<li>${finding}</li>`).join("");
  const themes = project.evidence
    .map((item) => `<tr><td>${item.theme}</td><td>${item.count}</td><td>${item.summary}</td></tr>`)
    .join("");

  if (role === "client") {
    return {
      fileName: `${safeFilePart(project.title)}-executive-delivery-report.doc`,
      mimeType: "application/msword;charset=utf-8",
      contents: `<!doctype html><html><head><meta charset="utf-8"><title>${project.title} — Executive delivery report</title></head><body><h1>${project.title}</h1><p>Executive delivery report</p><h2>Project summary</h2><p>${project.description}</p><h2>Key findings</h2><ul>${findings}</ul><p>This delivery report contains approved findings prepared for stakeholder review.</p></body></html>`,
    };
  }

  return {
    fileName: `${safeFilePart(project.title)}-internal-research-report.doc`,
    mimeType: "application/msword;charset=utf-8",
    contents: `<!doctype html><html><head><meta charset="utf-8"><title>${project.title} — Internal research report</title></head><body><h1>${project.title}</h1><p>Internal research report</p><p>${project.description}</p><h2>Research ownership</h2><p>Project owner: ${project.owner}</p><h2>Session operations</h2><p>Completed sessions: ${project.sessions.completed}/${project.sessions.total} · Evidence count: ${project.evidenceCount} · Last updated: ${project.updatedAt}</p><h2>Key findings</h2><ul>${findings}</ul><h2>Internal evidence detail</h2><table border="1" cellspacing="0" cellpadding="6"><thead><tr><th>Theme</th><th>Evidence count</th><th>Summary</th></tr></thead><tbody>${themes}</tbody></table></body></html>`,
  };
};

export const makePowerBiDataset = (project: ResearchProject): DownloadPayload => {
  const rows = project.evidence
    .map((item) => `"${item.theme.replace(/\"/g, '\"\"')}",${item.count},"${item.summary.replace(/\"/g, '\"\"')}"`)
    .join("\n");

  return {
    fileName: `${safeFilePart(project.title)}-power-bi-dataset.csv`,
    mimeType: "text/csv;charset=utf-8",
    contents: `segment,evidence_count,summary\n${rows}`,
  };
};

export const downloadPayload = (payload: DownloadPayload): void => {
  const blob = new Blob(["\uFEFF", payload.contents], { type: payload.mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = payload.fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
};
