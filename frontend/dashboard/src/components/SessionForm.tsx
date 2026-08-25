import { useEffect, useState, type Dispatch, type SetStateAction } from "react";
import {
  createProject,
  createSession,
  deleteProject,
  deleteSession,
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

type View = "new-project" | "new-session" | "session-list" | "manage-projects" | null;

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
  const [presetProjectId, setPresetProjectId] = useState(
    () => new URLSearchParams(window.location.search).get("project") ?? "",
  );
  const [view, setView] = useState<View>(() => {
    const p = new URLSearchParams(window.location.search).get("project");
    return p ? "session-list" : null;
  });
  const [projects, setProjects] = useState<Project[]>([]);

  useEffect(() => {
    let cancelled = false;
    // 페이지 로드 직후 첫 요청이 간헐적으로 실패하는 경우가 있어 짧게 재시도한다.
    const loadProjects = async (attempt = 0) => {
      try {
        const result = await listProjects();
        if (!cancelled) setProjects(result);
      } catch (cause) {
        if (attempt < 4) {
          setTimeout(() => loadProjects(attempt + 1), 500 * (attempt + 1));
        } else {
          console.error("프로젝트 목록 조회 실패", cause);
        }
      }
    };
    loadProjects();
    return () => {
      cancelled = true;
    };
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
            <button type="button" className="dock-icon project" title="프로젝트 생성 및 삭제" onClick={() => setView("manage-projects")}>
              <span className="dock-icon-glyph">
                <svg width="21" height="21" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3.5 5.75A1.75 1.75 0 0 1 5.25 4h3l1.5 1.75h5A1.75 1.75 0 0 1 16.5 7.5v7A1.75 1.75 0 0 1 14.75 16h-9A1.75 1.75 0 0 1 4 14.25v-8.5z" />
                  <path d="M10 8.5v4M8 10.5h4" />
                </svg>
              </span>
              <span className="dock-icon-label">프로젝트 생성 및 삭제</span>
              <span className="dock-icon-help">프로젝트를 만들거나 관리·삭제합니다</span>
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
      {view === "session-list" && (
        <SessionListView
          projects={projects}
          presetProjectId={presetProjectId}
          onCreated={onCreated}
        />
      )}
      {view === "manage-projects" && <ProjectManageView projects={projects} setProjects={setProjects} />}
    </main>
  );
}

const FILE_FORMATS = [
  { key: "md", label: "Markdown", accept: ".md,text/markdown" },
  {
    key: "word",
    label: "Word",
    accept: ".doc,.docx,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  },
  { key: "pdf", label: "PDF", accept: ".pdf,application/pdf" },
] as const;

type FileFormat = (typeof FILE_FORMATS)[number]["key"];

function NewProjectView({ onCreated }: { onCreated: (project: Project) => void }) {
  const [method, setMethod] = useState<"guide" | "manual">("guide");
  const [fileFormat, setFileFormat] = useState<FileFormat>("md");
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
      if (method === "guide") {
        const result = await uploadGuideFile(guideFile as File);
        alert(`✅ 가이드라인 분석 완료!\n주제: ${result.study.title}\n추출된 질문 수: ${result.study.questions.length}개`);
        setCreated(result.study as Project);
      } else {
        const result = await createProject({
          title: title.trim(),
          research_purpose: purpose.trim(),
          question_script: questionScript.trim(),
        });
        setCreated(result.study as Project);
      }
    } catch (cause: any) {
      const msg = cause instanceof Error ? cause.message : String(cause);
      setError(msg);
      alert(`❌ 프로젝트 생성/파싱 실패: ${msg}`);
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
        <ProjectAccessIdCard accessId={created.access_id} />
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
          <div style={{ marginTop: 16 }}>
            <p className="m-sub" style={{ marginBottom: 8, fontSize: "0.88rem", color: "var(--muted, #888)" }}>파일로 질문지를 가져올 형식을 선택하세요</p>
            <div className="format-seg" style={{ display: "flex", gap: 8, marginBottom: 12 }}>
              {FILE_FORMATS.map((format) => (
                <button
                  key={format.key}
                  type="button"
                  className={fileFormat === format.key ? "on" : ""}
                  onClick={() => {
                    setFileFormat(format.key);
                    setGuideFile(null);
                  }}
                >
                  {format.label}
                </button>
              ))}
            </div>

            <label className="guide-upload-field">
              <span className="guide-upload-icon" aria-hidden="true">↑</span>
              <strong>질문 가이드 파일을 올려주세요</strong>
              <small>{fileFormat.toUpperCase()} 형식 · AI가 질문 트리를 생성합니다.</small>
              <input
                key={fileFormat}
                type="file"
                accept={FILE_FORMATS.find((f) => f.key === fileFormat)?.accept}
                onChange={(event) => setGuideFile(event.target.files?.[0] ?? null)}
              />
              {guideFile && <span className="guide-file-name">선택된 파일: {guideFile.name}</span>}
            </label>
          </div>
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
            {busy ? "AI 파싱 중…" : "새 프로젝트 만들기"}
          </button>
        </div>
        {error && <p className="error">{error}</p>}
      </div>
    </section>
  );
}

export function ProjectAccessIdCard({ accessId }: { accessId?: string | null }) {
  const [copied, setCopied] = useState(false);

  if (!accessId) return null;

  const copyAccessId = async () => {
    await navigator.clipboard.writeText(accessId);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  return (
    <section className="project-access-id-card" aria-label="Client Access ID">
      <div>
        <p>CLIENT DELIVERY</p>
        <strong>Client Access ID</strong>
        <code>{accessId}</code>
      </div>
      <button type="button" className="btn-sm solid" onClick={copyAccessId}>
        {copied ? "복사됨" : "ID 복사"}
      </button>
      <small>이 ID를 Client에게 전달하면 해당 프로젝트 결과만 확인할 수 있습니다.</small>
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
  const selectedProject = projects.find((project) => project.id === projectId);

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
            <ProjectAccessIdCard accessId={selectedProject?.access_id} />

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
  presetProjectId = "",
  onCreated,
}: {
  projects: Project[];
  presetProjectId?: string;
  onCreated: (session: Session, intervieweeUrl: string) => void;
}) {
  const [projectId, setProjectId] = useState(presetProjectId || "");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (presetProjectId && !projectId) {
      setProjectId(presetProjectId);
    }
  }, [presetProjectId]);

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

function ProjectManageView({
  projects,
  setProjects,
}: {
  projects: Project[];
  setProjects: Dispatch<SetStateAction<Project[]>>;
}) {
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const selectedProject = projects.find((project) => project.id === selectedProjectId) ?? null;

  const handleDeleteProject = async (project: Project) => {
    if (
      !window.confirm(
        `"${project.title}" 프로젝트를 삭제할까요?\n이 프로젝트의 인터뷰 세션도 모두 함께 삭제됩니다.`,
      )
    ) {
      return;
    }
    setError("");
    setBusyId(project.id);
    try {
      await deleteProject(project.id);
      setProjects((prev) => prev.filter((item) => item.id !== project.id));
      if (selectedProjectId === project.id) setSelectedProjectId(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusyId(null);
    }
  };

  if (creating) {
    return (
      <NewProjectView
        onCreated={(project) => {
          setProjects((current) => [project, ...current.filter((item) => item.id !== project.id)]);
          setCreating(false);
        }}
      />
    );
  }

  if (selectedProject) {
    return (
      <ProjectDetailView
        project={selectedProject}
        onBack={() => setSelectedProjectId(null)}
        onDeleteProject={() => handleDeleteProject(selectedProject)}
        deletingProject={busyId === selectedProject.id}
      />
    );
  }

  return (
    <section className="panel">
      <header className="p-head">
        <div>
          <h2>프로젝트 생성 및 삭제</h2>
          <div className="sub">프로젝트를 새로 만들거나, 목록에서 선택해 세션까지 관리·삭제하세요</div>
        </div>
      </header>
      <div className="p-body">
        <div className="form-actions" style={{ marginBottom: 12 }}>
          <button type="button" onClick={() => setCreating(true)}>
            + 새 프로젝트 만들기
          </button>
        </div>

        {projects.length === 0 && <p className="muted small">등록된 프로젝트가 없습니다.</p>}

        {projects.map((project) => (
          <div key={project.id} className="project-row">
            <button
              type="button"
              className="project-row-title row-main"
              onClick={() => setSelectedProjectId(project.id)}
            >
              <strong>{project.title}</strong>
              <span className="desc">{new Date(project.created_at).toLocaleString("ko-KR")}</span>
            </button>
            <button
              type="button"
              className="btn-sm danger"
              disabled={busyId === project.id}
              onClick={() => handleDeleteProject(project)}
            >
              {busyId === project.id ? "삭제 중…" : "삭제"}
            </button>
          </div>
        ))}
        {error && <p className="error">{error}</p>}
      </div>
    </section>
  );
}

function ProjectDetailView({
  project,
  onBack,
  onDeleteProject,
  deletingProject,
}: {
  project: Project;
  onBack: () => void;
  onDeleteProject: () => void;
  deletingProject: boolean;
}) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    // 페이지 로드 직후 첫 요청이 간헐적으로 실패하는 경우가 있어 짧게 재시도한다.
    const loadSessions = async (attempt = 0) => {
      try {
        const result = await listProjectSessions(project.id);
        if (!cancelled) setSessions(result);
        if (!cancelled) setLoading(false);
      } catch (cause) {
        if (attempt < 4) {
          setTimeout(() => loadSessions(attempt + 1), 500 * (attempt + 1));
        } else {
          console.error("세션 목록 조회 실패", cause);
          if (!cancelled) setLoading(false);
        }
      }
    };
    loadSessions();
    return () => {
      cancelled = true;
    };
  }, [project.id]);

  const handleDeleteSession = async (session: Session) => {
    if (!window.confirm(`세션 "${formatSessionReference(session.id)}"을(를) 삭제할까요?`)) return;
    setError("");
    setBusyId(session.id);
    try {
      await deleteSession(session.id);
      setSessions((prev) => prev.filter((item) => item.id !== session.id));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <section className="panel">
      <header className="p-head">
        <div>
          <button type="button" className="ghost" style={{ marginBottom: 8 }} onClick={onBack}>
            ← 목록으로
          </button>
          <h2>{project.title}</h2>
          <div className="sub">{project.research_purpose}</div>
        </div>
        <button type="button" className="btn-sm danger" disabled={deletingProject} onClick={onDeleteProject}>
          {deletingProject ? "삭제 중…" : "이 프로젝트 삭제"}
        </button>
      </header>
      <div className="p-body">
        <h3 style={{ fontSize: 13, margin: "4px 0 8px" }}>인터뷰 세션</h3>
        {loading && <p className="muted small">불러오는 중…</p>}
        {!loading && sessions.length === 0 && (
          <p className="muted small">이 프로젝트엔 아직 생성된 세션이 없습니다.</p>
        )}
        {sessions.map((session) => (
          <div key={session.id} className="project-row">
            <span className="row-main">
              <span className={`badge ${session.status === "running" ? "connected" : ""}`}>
                {STATUS_LABEL[session.status]}
              </span>{" "}
              <code>{formatSessionReference(session.id)}</code>
              <span className="desc">{new Date(session.created_at).toLocaleString("ko-KR")}</span>
            </span>
            <button
              type="button"
              className="btn-sm danger"
              disabled={busyId === session.id}
              onClick={() => handleDeleteSession(session)}
            >
              {busyId === session.id ? "삭제 중…" : "삭제"}
            </button>
          </div>
        ))}
        {error && <p className="error">{error}</p>}
      </div>
    </section>
  );
}
