import { ChartBar, CheckCircle, CircleNotch, Gauge, ListChecks } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import type { UserRole } from "../../auth/RoleContext";
import type { ClientResearchSession } from "../../lib/researchSessions";
import type { DashboardMode, ResearchProject } from "../../mock/researchProjects";
import {
  getDashboardView,
  getFocusedEvidence,
  getPermittedDashboardMode,
  getVisualBarWidth,
} from "../../lib/researchInsights";

const dashboardControls: Array<{ id: DashboardMode; label: string; icon: typeof ChartBar }> = [
  { id: "evidence", label: "Evidence", icon: ChartBar },
  { id: "coverage", label: "Coverage", icon: Gauge },
  { id: "session", label: "세션 상태", icon: ListChecks },
];

interface InsightDashboardProps {
  project: ResearchProject;
  role: UserRole;
  linkedSession?: ClientResearchSession;
}

export default function InsightDashboard({ project, role, linkedSession }: InsightDashboardProps) {
  const [mode, setMode] = useState<DashboardMode>("evidence");
  const [activeTheme, setActiveTheme] = useState(project.evidence[0]?.theme ?? "");
  const permittedMode = getPermittedDashboardMode(role, mode);
  const view = getDashboardView(project, permittedMode);
  const largestBar = Math.max(...view.bars.map((bar) => bar.count), 1);
  const isProcessing = project.status === "processing";
  const focusedEvidence = getFocusedEvidence(project, permittedMode, activeTheme);
  const availableControls = dashboardControls.filter((control) => role === "pm" || control.id !== "session");

  useEffect(() => {
    if (mode === permittedMode) return;

    setMode(permittedMode);
    setActiveTheme(getDashboardView(project, permittedMode).bars[0]?.theme ?? "");
  }, [mode, permittedMode, project]);

  useEffect(() => {
    if (!linkedSession) return;

    const theme = project.sessionThemeMap?.[linkedSession.dashboardTheme] ?? linkedSession.dashboardTheme;
    const hasLinkedTheme = project.evidence.some((item) => item.theme === theme);
    if (!hasLinkedTheme) return;

    setMode("evidence");
    setActiveTheme(theme);
  }, [linkedSession, project]);

  const selectMode = (nextMode: DashboardMode) => {
    const nextView = getDashboardView(project, nextMode);
    setMode(nextMode);
    setActiveTheme(nextView.bars[0]?.theme ?? "");
  };

  return (
    <section className="insight-dashboard" aria-labelledby="dashboard-title">
      <div className="insight-dashboard__topline">
        <div>
          <p className="research-eyebrow">Research view</p>
          <h2 id="dashboard-title">보고 싶은 관점으로 결과를 읽으세요.</h2>
        </div>
        {role === "pm" ? <span className={`research-status research-status--${project.status}`}>
          {isProcessing ? <CircleNotch size={15} className="research-spin" /> : <CheckCircle size={15} weight="fill" />}
          {isProcessing ? "수집 및 분석 진행 중" : "리포트 준비 완료"}
        </span> : null}
      </div>

      <div className="insight-dashboard__controls" role="group" aria-label="분석 관점">
        {availableControls.map((control) => {
          const Icon = control.icon;
          const isActive = permittedMode === control.id;

          return (
            <button
              type="button"
              key={control.id}
              className={isActive ? "insight-dashboard__control is-active" : "insight-dashboard__control"}
              onClick={() => selectMode(control.id)}
              aria-pressed={isActive}
            >
              <Icon size={18} weight={isActive ? "fill" : "regular"} />
              {control.label}
            </button>
          );
        })}
      </div>

      <div className="insight-dashboard__content" key={permittedMode}>
        <div className="insight-dashboard__summary">
          <p className="research-eyebrow">{view.totalLabel}</p>
          <p className="insight-dashboard__total">
            {view.totalValue}<small>{view.unit}</small>
          </p>
          <p>{view.description}</p>
          <div className="insight-dashboard__legend">
            <span><i className="legend-dot legend-dot--blue" />확인된 신호</span>
            <span><i className="legend-dot legend-dot--muted" />다음 확인 항목</span>
          </div>
        </div>

        <div className="insight-dashboard__chart" aria-live="polite">
          <div className="insight-dashboard__chart-heading">
            <div>
              <p>{view.title}</p>
              <span>프로젝트 데이터 기준</span>
            </div>
            <span className="insight-dashboard__chart-count">{view.bars.length} themes</span>
          </div>
          <div className="insight-dashboard__bars">
            {view.bars.map((bar, index) => {
              const width = getVisualBarWidth(bar.count, largestBar);

              const isActive = activeTheme === bar.theme;

              return (
                <button
                  type="button"
                  className={`insight-dashboard__bar-row${isActive ? " is-active" : ""}`}
                  key={bar.theme}
                  onClick={() => setActiveTheme(bar.theme)}
                  aria-pressed={isActive}
                  aria-label={`${bar.theme} 근거에 집중`}
                >
                  <div className="insight-dashboard__bar-label">
                    <span>{bar.theme}</span>
                    <strong>{permittedMode === "coverage" ? `${bar.count}%` : bar.count}</strong>
                  </div>
                  <div className="insight-dashboard__bar-track">
                    <span
                      className={`insight-dashboard__bar-fill insight-dashboard__bar-fill--${index}`}
                      style={{ width: `${width}%` }}
                    />
                  </div>
                  <p>{bar.summary}</p>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <article className="insight-dashboard__focus-card" aria-live="polite" aria-labelledby="focused-evidence-title">
        <div className="insight-dashboard__focus-heading">
          <div>
            <p className="research-eyebrow">Focused evidence</p>
            <h3 id="focused-evidence-title">{focusedEvidence.theme}</h3>
          </div>
          {role === "pm" ? <span>{focusedEvidence.sessionCount} linked sessions</span> : null}
        </div>
        <p className="insight-dashboard__focus-summary">{focusedEvidence.summary}</p>
        <blockquote>“{focusedEvidence.quote}”</blockquote>
        <div className="insight-dashboard__focus-action">
          <strong>Recommended action</strong>
          <p>{focusedEvidence.nextAction}</p>
        </div>
        {role === "pm" && linkedSession ? <p className="insight-dashboard__linked-session">Selected session: {linkedSession.participantSegment}</p> : null}
      </article>

      <div className="insight-dashboard__kpis" aria-label="프로젝트 핵심 지표">
        <div><span>Evidence</span><strong>{project.evidenceCount}</strong></div>
        <div><span>Key findings</span><strong>{project.keyFindingCount}</strong></div>
        {role === "pm" ? <><div><span>Completed sessions</span><strong>{project.sessions.completed}/{project.sessions.total}</strong></div><div><span>Research gaps</span><strong>{project.researchGaps}</strong></div></> : null}
      </div>
    </section>
  );
}
