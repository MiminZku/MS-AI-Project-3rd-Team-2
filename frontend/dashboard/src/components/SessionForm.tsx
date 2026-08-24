import { useEffect, useState } from "react";
import {
  createProject,
  createSession,
  fetchSession,
  listProjects,
  listProjectSessions,
  uploadGuideFile,
} from "../api";
import type { Project, Session } from "../types";
import {
  formatSessionReference,
  normalizeParticipantId,
  validateParticipantId,
} from "../lib/sessionIdentity";

const STATUS_LABEL: Record<Session["status"], string> = {
  created: "대기",
  running: "진행중",
  ended: "종료",
};

type View = "new-project" | "new-session" | "session-list" | null;

interface Props {
  role: "pm" | "client";
  onCreated: (session: Session, intervieweeUrl: string) => void;
}

export function SessionListRows({
  sessions,
  busy,
  onOpen,
}: {
  sessions: Session[];
  busy: boolean;
  onOpen: (session: Session) => void;
}) {
  return (
    <>
      {sessions.map((session) => {
        const ended = session.status === "ended";
        return (
          <button
            key={session.id}
            type="button"
            className="link-row"
            style={{ width: "100%", cursor: ended ? "not-allowed" : "pointer", textAlign: "left" }}
            disabled={busy || ended}
            onClick={() => onOpen(session)}
          >
            <span className={`badge ${session.status === "running" ? "connected" : ""}`}>
              {STATUS_LABEL[session.status]}
            </span>
            <code>{formatSessionReference(session.id)}</code>
            <span className="desc" style={{ width: "100%", margin: "4px 0 0" }}>
              {new Date(session.created_at).toLocaleString("ko-KR")}
            </span>
          </button>
        );
      })}
    </>
  );
}

export default function SessionForm({ role, onCreated }: Props) {
  const [view, setView] = useState<View>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [presetProjectId, setPresetProjectId] = useState(
    () => new URLSearchParams(window.location.search).get("project") ?? "",
  );

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch((cause: unknown) => console.error("프로젝트 목록 조회 실패", cause));
  }, []);

  if (view === null) {
    return (
      <main className="form-page picker">
        <section className="picker-intro" aria-labelledby="dashboard-title">
          <p className="picker-eyebrow">Gromit research control</p>
          <h1 id="dashboard-title">참관자 대시보드</h1>
          <p>
            {role === "pm"
              ? "새 조사를 시작하거나, 진행 중인 프로젝트의 인터뷰 세션을 관리하세요."
              : "참여 중인 프로젝트의 인터뷰 세션과 승인된 진행 상태를 확인하세요."}
          </p>
        </section>

        <div className="dock dashboard-action-grid">
          {role === "pm" && (
            <button type="button" className="dock-icon project" title="새 프로젝트 만들기" onClick={() => setView("new-project")}>
              <span className="dock-icon-glyph">
                <svg width="21" height="21" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3.5 5.75A1.75 1.75 0 0 1 5.25 4h3l1.5 1.75h5A1.75 1.75 0 0 1 16.5 7.5v7A1.75 1.75 0 0 1 14.75 16h-9A1.75 1.75 0 0 1 4 14.25v-8.5z" />
                  <path d="M10 8.5v4M8 10.5h4" />
                </svg>
              </span>
              <span className="dock-icon-label">새 프로젝트 만들기</span>
              <span className="dock-icon-help">새 주제와 질문 가이드를 등록합니다</span>
            </button>
          )}
          {role === "pm" && (
            <button type="button" className="dock-icon session" title="새 인터뷰 세션" onClick={() => setView("new-session")}>
              <span className="dock-icon-glyph">
                <svg width="21" height="21" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="10" cy="10" r="8" />
                  <path d="M8.2 6.8l5 3.2-5 3.2V6.8z" fill="currentColor" stroke="none" />
                </svg>
              </span>
              <span className="dock-icon-label">새 인터뷰 세션</span>
              <span className="dock-icon-help">기존 프로젝트에서 인터뷰를 시작합니다</span>
            </button>
          )}
          <button type="button" className="dock-icon list" title="세션 목록" onClick={() => setView("session-list")}>
            <span className="dock-icon-glyph">
              <svg width="21" height="21" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 5.5h12M4 10h12M4 14.5h9" />
              </svg>
            </span>
            <span className="dock-icon-label">세션 목록</span>
            <span className="dock-icon-help">프로젝트별 진행 상태를 확인합니다</span>
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

      {view === "new-project" && (
        <NewProjectView
          onCreated={(project) => {
            setProjects((current) => [project, ...current.filter((item) => item.id !== project.id)]);
            setPresetProjectId(project.id);
            setView("new-session");
          }}
        />
      )}
      {view === "new-session" && (
        <NewSessionView
          projects={projects}
          presetProjectId={presetProjectId}
          onCreated={onCreated}
        />
      )}
      {view === "session-list" && <SessionListView projects={projects} onCreated={onCreated} />}
    </main>
  );
}

function NewProjectView({ onCreated }: { onCreated: (project: Project) => void }) {
  const [method, setMethod] = useState<"guide" | "manual">("guide");
  const [guideFile, setGuideFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [purpose, setPurpose] = useState("");
  const [questionScript, setQuestionScript] = useState("");
  const [created, setCreated] = useState<Project | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async () => {
    setError("");
    if (method === "guide" && !guideFile) {
      setError("질문 가이드 파일을 선택해 주세요.");
      return;
    }
    if (method === "manual" && (!title.trim() || !purpose.trim() || !questionScript.trim())) {
      setError("프로젝트명, 조사 목적, 질문지를 모두 입력해 주세요.");
      return;
    }

    setBusy(true);
    try {
      const result = method === "guide"
        ? await uploadGuideFile(guideFile as File)
        : await createProject({
          title: title.trim(),
          research_purpose: purpose.trim(),
          question_script: questionScript.trim(),
        });
      setCreated(result.study as Project);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  };

  if (created) {
    return (
      <section className="panel project-create-panel project-success-panel">
        <div className="project-success-icon" aria-hidden="true">✓</div>
        <p className="picker-eyebrow">PROJECT READY</p>
        <h2>{created.title}</h2>
        <p className="project-success-copy">질문 구조가 등록되었습니다. 지금 바로 첫 인터뷰 세션을 만들 수 있습니다.</p>
        <div className="project-success-meta">
          <span>질문 {created.questions.length}개</span>
          <span>{created.research_purpose}</span>
        </div>
        <div className="form-actions project-success-actions">
          <button type="button" className="btn-ghost" onClick={() => setCreated(null)}>다른 프로젝트 만들기</button>
          <button type="button" onClick={() => onCreated(created)}>이 프로젝트로 세션 만들기</button>
        </div>
      </section>
    );
  }

  return (
    <section className="panel project-create-panel">
      <header className="p-head project-create-head">
        <div>
          <p className="picker-eyebrow">NEW RESEARCH</p>
          <h2>새 프로젝트 만들기</h2>
          <div className="sub">조사 주제와 질문 가이드를 등록하면, 프로젝트별 인터뷰와 결과를 계속 관리할 수 있습니다.</div>
        </div>
      </header>
      <div className="p-body">
        <div className="project-method-tabs" role="tablist" aria-label="프로젝트 생성 방식">
          <button className={method === "guide" ? "on" : ""} role="tab" aria-selected={method === "guide"} type="button" onClick={() => setMethod("guide")}>
            가이드 파일 업로드
          </button>
          <button className={method === "manual" ? "on" : ""} role="tab" aria-selected={method === "manual"} type="button" onClick={() => setMethod("manual")}>
            질문지 직접 작성
          </button>
        </div>

        {method === "guide" ? (
          <label className="guide-upload-field">
            <span className="guide-upload-icon" aria-hidden="true">↑</span>
            <strong>질문 가이드 파일을 올려주세요</strong>
            <small>Word(.docx), PDF, Markdown(.md) · AI가 질문 트리를 생성합니다.</small>
            <input
              accept=".docx,.pdf,.md,text/markdown,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={(event) => setGuideFile(event.target.files?.[0] ?? null)}
              type="file"
            />
            {guideFile && <span className="guide-file-name">선택된 파일: {guideFile.name}</span>}
          </label>
        ) : (
          <div className="project-manual-fields">
            <label>
              프로젝트명
              <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="예: 모바일 뱅킹 앱 사용성 조사" />
            </label>
            <label>
              조사 목적
              <input value={purpose} onChange={(event) => setPurpose(event.target.value)} placeholder="예: 이체 흐름의 신뢰와 이해도를 파악합니다." />
            </label>
            <label>
              인터뷰 질문지
              <textarea value={questionScript} onChange={(event) => setQuestionScript(event.target.value)} placeholder={'1. 최근 사용 경험을 들려주세요.\n2. 가장 어려웠던 단계는 무엇인가요?'} />
            </label>
          </div>
        )}

        <div className="form-actions project-create-actions">
          <button disabled={busy} onClick={submit} type="button">
            {busy ? "프로젝트를 준비하는 중…" : "새 프로젝트 만들기"}
          </button>
        </div>
        {error && <p className="error">{error}</p>}
      </div>
    </section>
  );
}

export function NewSessionView({
  projects,
  presetProjectId,
  onCreated,
}: {
  projects: Project[];
  presetProjectId: string;
  onCreated: (session: Session, intervieweeUrl: string) => void;
}) {
  const [projectId, setProjectId] = useState(presetProjectId);
  const [participantId, setParticipantId] = useState("");
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
    setError("");
    const participantIdError = validateParticipantId(participantId);
    if (participantIdError) {
      setError(participantIdError);
      return;
    }
    setBusy(true);
    try {
      const result = await createSession({
        title: normalizeParticipantId(participantId),
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
              참가자 ID
              <p className="desc">실명 대신 인터뷰 참여자를 구분하는 익명 ID를 입력하세요 (예: INT-001)</p>
              <input
                type="text"
                value={participantId}
                onChange={(event) => setParticipantId(event.target.value)}
                placeholder="INT-001"
                autoCapitalize="characters"
                maxLength={40}
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

        <SessionListRows sessions={sessions} busy={busy} onOpen={open} />
        {error && <p className="error">{error}</p>}
      </div>
    </section>
  );
}
