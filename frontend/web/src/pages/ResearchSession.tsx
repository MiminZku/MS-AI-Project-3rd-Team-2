import { ArrowLeft } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import { useRole } from "../auth/RoleContext";
import SessionDetail from "../components/research/SessionDetail";
import { getProjectById } from "../lib/researchInsights";
import { getPmResearchSession, getResearchSession, getSessionRedirectPath, type ResearchSession } from "../lib/researchSessions";

export default function ResearchSession() {
  const { projectId, sessionId } = useParams<{ projectId: string; sessionId: string }>();
  const { role } = useRole();
  const project = projectId ? getProjectById(projectId) : undefined;
  const clientSession = projectId && sessionId ? getResearchSession(projectId, sessionId) : undefined;
  const [pmSession, setPmSession] = useState<ResearchSession | null>();

  useEffect(() => {
    if (role !== "pm" || !projectId || !sessionId) return;
    let active = true;
    setPmSession(undefined);
    void getPmResearchSession(projectId, sessionId).then((session) => {
      if (active) setPmSession(session ?? null);
    });
    return () => { active = false; };
  }, [projectId, role, sessionId]);

  if (!project) return <Navigate to="/projects" replace />;
  if (!role) return <Navigate to={`/projects/${project.id}/results`} replace />;
  if (role === "client" && (!clientSession || getSessionRedirectPath(project.id, sessionId ?? ""))) return <Navigate to={`/projects/${project.id}/results`} replace />;
  if (role === "pm" && pmSession === undefined) return <div className="research-session-page" />;
  if (role === "pm" && !pmSession) return <Navigate to={`/projects/${project.id}/results`} replace />;
  const session = role === "pm" ? pmSession : clientSession;

  return (
    <div className="research-session-page">
      <section className="research-session-hero">
        <div className="container">
          <Link className="research-back-link" to={`/projects/${project.id}/results`}><ArrowLeft size={16} weight="bold" />Back to project results</Link>
          <SessionDetail role={role} session={session!} />
        </div>
      </section>
    </div>
  );
}
