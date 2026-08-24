import { ArrowLeft, ArrowRight, Lightbulb, WarningCircle } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import { useRole } from "../auth/RoleContext";
import DirectDownloads from "../components/research/DirectDownloads";
import InsightDashboard from "../components/research/InsightDashboard";
import SessionList from "../components/research/SessionList";
import { getProjectById } from "../lib/researchInsights";
import { getPmProjectSessions, getPmResearchSession, getProjectSessions, getResearchSession, type ResearchSession } from "../lib/researchSessions";

export default function ResearchResults() {
  const { projectId } = useParams<{ projectId: string }>();
  const project = projectId ? getProjectById(projectId) : undefined;
  const { role } = useRole();
  const [selectedSessionId, setSelectedSessionId] = useState<string>();
  const [pmLinkedSession, setPmLinkedSession] = useState<ResearchSession>();

  useEffect(() => {
    if (!project || !role) return;

    if (role === "client") {
      const clientSessions = getProjectSessions(project.id);
      setSelectedSessionId((current) => clientSessions.some((session) => session.id === current) ? current : clientSessions[0]?.id);
      return;
    }

    let active = true;
    void getPmProjectSessions(project.id).then((sessions) => {
      if (active) setSelectedSessionId((current) => sessions.some((session) => session.id === current) ? current : sessions[0]?.id);
    });
    return () => { active = false; };
  }, [project, role]);

  useEffect(() => {
    if (!project || role !== "pm" || !selectedSessionId) {
      setPmLinkedSession(undefined);
      return;
    }

    let active = true;
    void getPmResearchSession(project.id, selectedSessionId).then((session) => {
      if (active) setPmLinkedSession(session);
    });
    return () => { active = false; };
  }, [project, role, selectedSessionId]);

  if (!project) return <Navigate to="/projects" replace />;
  if (!role) return <Navigate to="/login" replace />;

  const linkedSession = role === "pm"
    ? pmLinkedSession
    : selectedSessionId ? getResearchSession(project.id, selectedSessionId) : undefined;

  return (
    <div className="research-results-page">
      <section className="research-results-hero">
        <div className="container">
          <Link className="research-back-link" to="/projects"><ArrowLeft size={16} weight="bold" />모든 프로젝트</Link>
          <div className="research-results-hero__grid">
            <div>
              <p className="research-eyebrow">Research results</p>
              <h1>{project.title}</h1>
              <p>{project.description}</p>
            </div>
            <dl className="research-results-hero__meta">
              {role === "pm" ? <><div><dt>Project owner</dt><dd>{project.owner}</dd></div><div><dt>Last updated</dt><dd>{project.updatedAt}</dd></div><div><dt>Session progress</dt><dd>{project.sessions.completed}/{project.sessions.total}</dd></div></> : <><div><dt>Evidence</dt><dd>{project.evidenceCount}</dd></div><div><dt>Key findings</dt><dd>{project.keyFindingCount}</dd></div></>}
            </dl>
          </div>
        </div>
      </section>

      <main className="research-results-page__body container">
        <InsightDashboard project={project} role={role} linkedSession={linkedSession} />

        <SessionList
          projectId={project.id}
          selectedSessionId={selectedSessionId}
          onSelect={(session) => setSelectedSessionId(session.id)}
        />

        <section className="research-highlights" aria-labelledby="research-highlights-title">
          <div className="research-highlights__intro">
            <p className="research-eyebrow">Key findings</p>
            <h2 id="research-highlights-title">팀이 다음에 논의할<br />가설과 확인 항목</h2>
          </div>
          <div className="research-highlights__list">
            {project.highlights.map((highlight, index) => (
              <article key={highlight}>
                <span>{index + 1}</span>
                <p>{highlight}</p>
              </article>
            ))}
          </div>
        </section>

        {role === "pm" && project.status === "processing" ? (
          <aside className="research-processing-note"><WarningCircle size={20} weight="fill" /><p>아직 진행 중인 조사입니다. 현재까지 수집된 신호를 볼 수 있지만, 최종 산출물 다운로드는 모든 분석이 끝난 뒤 열립니다.</p></aside>
        ) : null}

        <DirectDownloads project={project} role={role} />

        <Link className="research-next-project" to="/projects"><span><Lightbulb size={20} weight="duotone" />다른 주제도 비교해 보세요.</span><ArrowRight size={20} weight="bold" /></Link>
      </main>
    </div>
  );
}
