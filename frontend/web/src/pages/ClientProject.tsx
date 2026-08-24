import { useEffect, useState } from "react";
import { ChartBar, Clock, FileText, ShieldCheck } from "@phosphor-icons/react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import {
  ClientProjectApiError,
  type ClientProject,
  type ClientSession,
  fetchClientProject,
  fetchClientProjectSessions,
} from "../lib/clientProjectApi";
import {
  clearClientProjectGrant,
  loadClientProjectGrant,
} from "../lib/clientProjectGrant";

const statusLabel: Record<ClientSession["status"], string> = {
  created: "준비 중",
  running: "진행 중",
  ended: "완료",
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium" }).format(new Date(value));
}

export default function ClientProject() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const grant = loadClientProjectGrant();
  const [project, setProject] = useState<ClientProject | null>(null);
  const [sessions, setSessions] = useState<ClientSession[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!projectId || !grant || grant.projectId !== projectId) return;

    Promise.all([
      fetchClientProject(projectId, grant.accessToken),
      fetchClientProjectSessions(projectId, grant.accessToken),
    ])
      .then(([loadedProject, loadedSessions]) => {
        setProject(loadedProject);
        setSessions(loadedSessions);
      })
      .catch((cause: unknown) => {
        if (cause instanceof ClientProjectApiError && [401, 403, 404].includes(cause.status)) {
          clearClientProjectGrant();
          setError("프로젝트 접속 권한이 없거나 만료되었습니다.");
          return;
        }
        setError("프로젝트 정보를 불러오지 못했습니다.");
      });
  }, [grant?.accessToken, grant?.projectId, projectId]);

  if (!projectId || !grant || grant.projectId !== projectId) {
    return <Navigate to="/client/access" replace />;
  }

  const returnToAccess = () => {
    clearClientProjectGrant();
    navigate("/client/access", { replace: true });
  };

  if (error) {
    return (
      <main className="client-project-page client-project-page--message">
        <section className="client-project-message"><ShieldCheck size={28} weight="duotone" /><h1>{error}</h1><Link to="/client/access">Project Access ID 다시 입력</Link></section>
      </main>
    );
  }

  if (!project) {
    return <main className="client-project-page client-project-page--message"><p role="status">프로젝트를 불러오는 중...</p></main>;
  }

  const completedSessions = sessions.filter((session) => session.status === "ended").length;

  return (
    <main className="client-project-page">
      <header className="client-project-header">
        <div className="client-project-header__inner">
          <Link className="client-project-wordmark" to="/client/project/" onClick={(event) => { event.preventDefault(); returnToAccess(); }}>Gromit <span>Client</span></Link>
          <button type="button" onClick={returnToAccess}>다른 프로젝트 접속</button>
        </div>
      </header>
      <section className="client-project-hero">
        <div className="client-project-container">
          <p>PROJECT DELIVERY</p>
          <h1>{project.title}</h1>
          <span>프로젝트 결과 전용 공간 · {formatDate(project.created_at)} 생성</span>
        </div>
      </section>
      <section className="client-project-container client-project-content">
        <article className="client-project-purpose"><span><FileText size={22} weight="duotone" /></span><div><p>조사 목적</p><h2>{project.research_purpose}</h2></div></article>
        <section className="client-project-kpis" aria-label="프로젝트 현황">
          <article><ChartBar size={22} weight="duotone" /><strong>{sessions.length}</strong><span>인터뷰 세션</span></article>
          <article><ShieldCheck size={22} weight="duotone" /><strong>{completedSessions}</strong><span>완료된 세션</span></article>
          <article><Clock size={22} weight="duotone" /><strong>{sessions.filter((session) => session.status === "running").length}</strong><span>진행 중</span></article>
        </section>
        <section className="client-project-sessions" aria-labelledby="client-sessions-title">
          <div><p>INTERVIEW STATUS</p><h2 id="client-sessions-title">인터뷰 진행 현황</h2></div>
          {sessions.length === 0 ? <p className="client-project-empty">아직 연결된 인터뷰 세션이 없습니다.</p> : <div className="client-session-list">{sessions.map((session) => <article key={session.id}><span className={`client-session-status client-session-status--${session.status}`}>{statusLabel[session.status]}</span><div><strong>인터뷰 세션</strong><p>{formatDate(session.created_at)} · {session.duration_minutes}분</p></div></article>)}</div>}
        </section>
        <p className="client-project-security"><ShieldCheck size={16} weight="fill" /> 이 페이지는 전달받은 Project Access ID와 연결된 데이터만 표시합니다.</p>
      </section>
    </main>
  );
}
