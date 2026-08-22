import { useEffect, useState } from "react";
import { createSession, fetchSession, listProjects, listProjectSessions } from "../api";
import type { Project, Session } from "../types";

const STATUS_LABEL: Record<Session["status"], string> = {
  created: "대기",
  running: "진행중",
  ended: "종료",
};

type View = "new-session" | "session-list" | null;

interface Props {
  onCreated: (session: Session, intervieweeUrl: string) => void;
}

export default function SessionForm({ onCreated }: Props) {
  const [view, setView] = useState<View>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [presetProjectId] = useState(() => new URLSearchParams(window.location.search).get("project") ?? "");

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch((cause: unknown) => console.error("프로젝트 목록 조회 실패", cause));
  }, []);

  if (view === null) {
    return (
      <main className="form-page picker">
        <div className="dock">
          <button type="button" className="dock-icon session" title="새 인터뷰 세션" onClick={() => setView("new-session")}>
            <span className="dock-icon-glyph">
              <svg width="21" height="21" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="10" cy="10" r="8" />
                <path d="M8.2 6.8l5 3.2-5 3.2V6.8z" fill="currentColor" stroke="none" />
              </svg>
            </span>
            <span className="dock-icon-label">새 인터뷰 세션</span>
          </button>
          <button type="button" className="dock-icon list" title="세션 목록" onClick={() => setView("session-list")}>
            <span className="dock-icon-glyph">
              <svg width="21" height="21" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 5.5h12M4 10h12M4 14.5h9" />
              </svg>
            </span>
            <span className="dock-icon-label">세션 목록</span>
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="form-page">
      <button type="button" className="ghost back-to-picker" onClick={() => setView(null)}>
        ← 뒤로
      </button>

      {view === "new-session" && (
        <NewSessionView projects={projects} presetProjectId={presetProjectId} onCreated={onCreated} />
      )}
      {view === "session-list" && <SessionListView projects={projects} onCreated={onCreated} />}
    </main>
  );
}

function NewSessionView({
  projects,
  presetProjectId,
  onCreated,
}: {
  projects: Project[];
  presetProjectId: string;
  onCreated: (session: Session, intervieweeUrl: string) => void;
}) {
  const [projectId, setProjectId] = useState(presetProjectId);
  const [sessionName, setSessionName] = useState("");
  const [duration, setDuration] = useState(60);
  const [language, setLanguage] = useState("ko");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState<{ session: Session; intervieweeUrl: string } | null>(null);
  const [copied, setCopied] = useState(false);

  const copyLink = async (url: string) => {
    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const submit = async () => {
    setBusy(true);
    setError("");
    try {
      const project = projects.find((p) => p.id === projectId);
      const result = await createSession({
        title: sessionName.trim() || project?.title || "제목 없는 인터뷰",
        duration_minutes: duration,
        study_id: projectId,
        question_script: "",
      });
      setCreated({ session: result.session, intervieweeUrl: result.interviewee_url });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel">
      <header className="p-head">
        <div>
          <h2>새 인터뷰 세션</h2>
          <div className="sub">PM만 접근 · 생성 후 링크가 발급됩니다</div>
        </div>
      </header>
      <div className="p-body">
        {!created ? (
          <>
            <label>
              프로젝트
              {projects.length === 0 && (
                <p className="desc">등록된 프로젝트가 없습니다 — 프로젝트 관리 포털에서 먼저 만들어주세요.</p>
              )}
              <select value={projectId} onChange={(event) => setProjectId(event.target.value)}>
                <option value="" disabled>
                  프로젝트를 선택하세요
                </option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.title}
                  </option>
                ))}
              </select>
            </label>

            <label>
              인터뷰 세션 이름
              <p className="desc">프로젝트 하나에 인터뷰가 여러 개 붙을 수 있어 구분용 이름을 붙입니다</p>
              <input
                type="text"
                value={sessionName}
                onChange={(event) => setSessionName(event.target.value)}
                placeholder="예) 3번째 참가자 - 김OO"
              />
            </label>

            <div className="two">
              <label>
                인터뷰 시간
                <p className="desc">종료 예정 시각 계산에 사용됩니다</p>
                <select value={duration} onChange={(event) => setDuration(Number(event.target.value))}>
                  <option value={10}>10분</option>
                  <option value={30}>30분</option>
                  <option value={60}>60분</option>
                  <option value={90}>90분</option>
                </select>
              </label>

              <label>
                통역 언어
                <p className="desc">응답자 발화를 이 언어로 통역해 백룸에 전달합니다 (준비 중)</p>
                <select value={language} onChange={(event) => setLanguage(event.target.value)}>
                  <option value="ko">한국어</option>
                  <option value="en">English</option>
                  <option value="ja">日本語</option>
                </select>
              </label>
            </div>

            <div className="form-actions">
              <button disabled={busy || !projectId} onClick={submit}>
                인터뷰 세션 생성 →
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="linkrow">
              <span className="lk-tag">인터뷰이</span>
              <code>{created.intervieweeUrl}</code>
              <button type="button" className="btn-sm" onClick={() => copyLink(created.intervieweeUrl)}>
                {copied ? "복사됨" : "복사"}
              </button>
              <span className="desc" style={{ width: "100%", margin: "4px 0 0" }}>
                일회용 · 1회 입장 후 만료
              </span>
            </div>
            <div className="linkrow">
              <span className="lk-tag">클라이언트</span>
              <code>준비 중</code>
              <button type="button" className="btn-sm" disabled title="곧 지원 예정">
                복사
              </button>
              <span className="desc" style={{ width: "100%", margin: "4px 0 0" }}>
                관찰 전용 · 세션 종료 시 만료 (곧 지원 예정)
              </span>
            </div>
            <div className="form-actions">
              <button onClick={() => onCreated(created.session, created.intervieweeUrl)}>백룸 열기 →</button>
            </div>
          </>
        )}
        {error && <p className="error">{error}</p>}
      </div>
    </section>
  );
}

function SessionListView({
  projects,
  onCreated,
}: {
  projects: Project[];
  onCreated: (session: Session, intervieweeUrl: string) => void;
}) {
  const [projectId, setProjectId] = useState("");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!projectId) {
      setSessions([]);
      return;
    }
    setLoading(true);
    listProjectSessions(projectId)
      .then(setSessions)
      .catch((cause: unknown) => console.error("세션 목록 조회 실패", cause))
      .finally(() => setLoading(false));
  }, [projectId]);

  const open = async (session: Session) => {
    setBusy(true);
    setError("");
    try {
      const result = await fetchSession(session.id);
      onCreated(result.session, result.interviewee_url);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel">
      <header className="p-head">
        <div>
          <h2>세션 목록</h2>
          <div className="sub">프로젝트를 선택하면 그 프로젝트의 인터뷰들이 표시됩니다</div>
        </div>
      </header>
      <div className="p-body">
        <label>
          프로젝트
          <select value={projectId} onChange={(event) => setProjectId(event.target.value)}>
            <option value="">프로젝트를 선택하세요</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.title}
              </option>
            ))}
          </select>
        </label>

        {loading && <p className="muted small">불러오는 중…</p>}
        {!loading && projectId && sessions.length === 0 && (
          <p className="muted small">이 프로젝트엔 아직 생성된 세션이 없습니다.</p>
        )}

        {sessions.map((session) => {
          const ended = session.status === "ended";
          return (
            <button
              key={session.id}
              type="button"
              className="link-row"
              style={{ width: "100%", cursor: ended ? "not-allowed" : "pointer", textAlign: "left" }}
              disabled={busy || ended}
              onClick={() => open(session)}
            >
              <span className={`badge ${session.status === "running" ? "connected" : ""}`}>
                {STATUS_LABEL[session.status]}
              </span>
              <code>{session.title}</code>
              <span className="desc" style={{ width: "100%", margin: "4px 0 0" }}>
                {new Date(session.created_at).toLocaleString("ko-KR")}
              </span>
            </button>
          );
        })}
        {error && <p className="error">{error}</p>}
      </div>
    </section>
  );
}
