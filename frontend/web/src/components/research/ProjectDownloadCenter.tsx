import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowClockwise,
  ChatText,
  CheckCircle,
  DownloadSimple,
  FileDoc,
  FileText,
  VideoCamera,
  Warning,
} from "@phosphor-icons/react";
import { Link } from "react-router-dom";
import {
  adminHeaders,
  downloadFile,
  fetchProjectReport,
  fetchProjects,
  fetchProjectSessions,
  generateProjectReport,
  projectReportDownloadUrl,
  recordingDownloadUrl,
  transcriptDownloadUrl,
  type ProjectAggregateReport,
  type ResearchProjectSummary,
  type ResearchSessionSummary,
} from "../../lib/researchApi";

const STATUS_LABEL: Record<ResearchSessionSummary["status"], string> = {
  created: "준비 중",
  running: "진행 중",
  ended: "완료",
};

function formatDateTime(value: string | null): string {
  if (!value) return "-";
  return new Date(value).toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * 다운로드 센터의 실제 동작 영역.
 *
 * 프로젝트 선택 -> 해당 프로젝트의 인터뷰 목록 -> 프로젝트 리포트 생성/다운로드,
 * 인터뷰별 질문·답변 기록과 녹화 영상 다운로드까지 백엔드와 연동한다.
 */
export default function ProjectDownloadCenter() {
  const [projects, setProjects] = useState<ResearchProjectSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [sessions, setSessions] = useState<ResearchSessionSummary[]>([]);
  const [report, setReport] = useState<ProjectAggregateReport | null>(null);

  const [loadingProjects, setLoadingProjects] = useState(true);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [busyDownload, setBusyDownload] = useState<string>("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchProjects()
      .then((list) => {
        if (cancelled) return;
        setProjects(list);
        setSelectedId((current) => current || list[0]?.id || "");
      })
      .catch(() => {
        if (!cancelled) setError("프로젝트 목록을 불러오지 못했습니다. 백엔드 연결을 확인해 주세요.");
      })
      .finally(() => {
        if (!cancelled) setLoadingProjects(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const loadProjectDetail = useCallback(async (projectId: string) => {
    if (!projectId) return;
    setLoadingSessions(true);
    setError("");
    try {
      const [sessionList, reportSnapshot] = await Promise.all([
        fetchProjectSessions(projectId),
        fetchProjectReport(projectId).catch(() => null),
      ]);
      setSessions(sessionList);
      setReport(reportSnapshot);
    } catch {
      setError("인터뷰 목록을 불러오지 못했습니다.");
      setSessions([]);
      setReport(null);
    } finally {
      setLoadingSessions(false);
    }
  }, []);

  useEffect(() => {
    void loadProjectDetail(selectedId);
  }, [selectedId, loadProjectDetail]);

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedId) ?? null,
    [projects, selectedId],
  );

  const completedSessions = useMemo(
    () => sessions.filter((session) => session.status === "ended"),
    [sessions],
  );

  const reportReady = report?.status === "COMPLETED";

  const runDownload = async (key: string, url: string, headers: HeadersInit = {}) => {
    setBusyDownload(key);
    setError("");
    setNotice("");
    try {
      await downloadFile(url, headers);
    } catch (downloadError) {
      setError(
        downloadError instanceof Error
          ? downloadError.message
          : "다운로드에 실패했습니다.",
      );
    } finally {
      setBusyDownload("");
    }
  };

  const handleGenerateReport = async () => {
    if (!selectedId) return;
    setGenerating(true);
    setError("");
    setNotice("");
    try {
      const generated = await generateProjectReport(selectedId);
      setReport(generated);
      if (generated.status === "COMPLETED") {
        setNotice(`리포트를 생성했습니다. (응답자 ${generated.respondent_count}명 기준)`);
      } else if (generated.status === "FAILED") {
        setError(generated.error_message ?? "리포트 생성에 실패했습니다.");
      }
    } catch (generateError) {
      setError(
        generateError instanceof Error
          ? generateError.message
          : "리포트 생성에 실패했습니다.",
      );
    } finally {
      setGenerating(false);
    }
  };

  if (loadingProjects) {
    return (
      <section className="download-center">
        <p className="download-center__empty">프로젝트를 불러오는 중입니다…</p>
      </section>
    );
  }

  return (
    <section className="download-center" aria-labelledby="download-center-title">
      <div className="research-section-heading research-section-heading--row">
        <div>
          <p className="research-eyebrow">Project deliverables</p>
          <h2 id="download-center-title">내 프로젝트 자료 받기</h2>
        </div>
        <button
          type="button"
          className="download-center__refresh"
          onClick={() => void loadProjectDetail(selectedId)}
          disabled={!selectedId || loadingSessions}
        >
          <ArrowClockwise size={16} weight="bold" />
          새로고침
        </button>
      </div>

      {projects.length === 0 ? (
        <p className="download-center__empty">
          아직 생성된 프로젝트가 없습니다. PM 대시보드에서 프로젝트를 먼저 만들어 주세요.
        </p>
      ) : (
        <>
          <label className="download-center__picker">
            <span>프로젝트 선택</span>
            <select value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.title}
                </option>
              ))}
            </select>
          </label>

          {selectedProject && (
            <p className="download-center__purpose">{selectedProject.research_purpose}</p>
          )}

          {error && (
            <p className="download-center__error" role="alert">
              <Warning size={16} weight="fill" />
              {error}
            </p>
          )}
          {notice && (
            <p className="download-center__notice" role="status">
              <CheckCircle size={16} weight="fill" />
              {notice}
            </p>
          )}

          {/* 프로젝트 단위 리포트 */}
          <article className="download-center__card">
            <div className="download-center__card-head">
              <span className="download-center__icon">
                <FileDoc size={20} weight="duotone" />
              </span>
              <div>
                <strong>프로젝트 종합 리포트</strong>
                <small>
                  완료된 인터뷰 {completedSessions.length}건
                  {reportReady && report?.generated_at
                    ? ` · 마지막 생성 ${formatDateTime(report.generated_at)}`
                    : " · 아직 생성 전"}
                </small>
              </div>
            </div>
            <div className="download-center__card-actions">
              <button
                type="button"
                className="download-center__btn"
                onClick={() => void handleGenerateReport()}
                disabled={generating || completedSessions.length === 0}
              >
                {generating ? "생성 중…" : reportReady ? "다시 생성" : "리포트 생성"}
              </button>
              <button
                type="button"
                className="download-center__btn download-center__btn--primary"
                onClick={() =>
                  void runDownload(
                    "project-report",
                    projectReportDownloadUrl(selectedId),
                    adminHeaders(),
                  )
                }
                disabled={!reportReady || busyDownload === "project-report"}
              >
                <DownloadSimple size={16} weight="bold" />
                {busyDownload === "project-report" ? "받는 중…" : "리포트 다운로드"}
              </button>
            </div>
            {completedSessions.length === 0 && (
              <p className="download-center__hint">
                완료된 인터뷰가 있어야 리포트를 생성할 수 있습니다.
              </p>
            )}
          </article>

          {/* 인터뷰 단위 다운로드 */}
          <h3 className="download-center__subtitle">인터뷰별 자료</h3>
          {loadingSessions ? (
            <p className="download-center__empty">인터뷰 목록을 불러오는 중입니다…</p>
          ) : sessions.length === 0 ? (
            <p className="download-center__empty">이 프로젝트에는 아직 인터뷰가 없습니다.</p>
          ) : (
            <ul className="download-center__sessions">
              {sessions.map((session) => {
                const transcriptKey = `transcript-${session.id}`;
                const recordingKey = `recording-${session.id}`;
                const isEnded = session.status === "ended";

                return (
                  <li key={session.id} className="download-center__session">
                    <div className="download-center__session-info">
                      <strong>{session.title}</strong>
                      <small>
                        <span className={`download-center__badge ${session.status}`}>
                          {STATUS_LABEL[session.status]}
                        </span>
                        {formatDateTime(session.started_at ?? session.created_at)} · 예정{" "}
                        {session.duration_minutes}분
                      </small>
                    </div>
                    <div className="download-center__session-actions">
                      {/* 파일로 받기 전에 화면에서 바로 읽을 수 있는 채팅 뷰 */}
                      <Link
                        to={`/transcripts/${selectedId}/${session.id}?title=${encodeURIComponent(session.title)}`}
                        className="download-center__btn download-center__btn--primary"
                      >
                        <ChatText size={15} weight="bold" />
                        기록 보기
                      </Link>
                      <button
                        type="button"
                        className="download-center__btn"
                        onClick={() =>
                          void runDownload(
                            transcriptKey,
                            transcriptDownloadUrl(session.id),
                            adminHeaders(),
                          )
                        }
                        disabled={busyDownload === transcriptKey}
                        title="질문·답변 기록 문서"
                      >
                        <FileText size={15} weight="bold" />
                        {busyDownload === transcriptKey ? "받는 중…" : "문서"}
                      </button>
                      <button
                        type="button"
                        className="download-center__btn"
                        onClick={() =>
                          void runDownload(
                            recordingKey,
                            recordingDownloadUrl(session.id),
                            adminHeaders(),
                          )
                        }
                        disabled={busyDownload === recordingKey || !session.video_recording_url}
                        title={
                          session.video_recording_url
                            ? "인터뷰 녹화 영상"
                            : "이 인터뷰에는 녹화본이 없습니다"
                        }
                      >
                        <VideoCamera size={15} weight="bold" />
                        {busyDownload === recordingKey ? "받는 중…" : "영상"}
                      </button>
                    </div>
                    {!isEnded && (
                      <p className="download-center__hint">
                        진행이 끝나면 기록이 확정됩니다.
                      </p>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </>
      )}
    </section>
  );
}
