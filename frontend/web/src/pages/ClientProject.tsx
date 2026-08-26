import { useEffect, useState } from "react";
import {
  ArrowsClockwise,
  Clock,
  DownloadSimple,
  FileDoc,
  FileText,
  Lock,
  PlayCircle,
  ShieldCheck,
  SignOut,
  VideoCamera,
  Warning,
} from "@phosphor-icons/react";
import { Navigate, useNavigate, useParams } from "react-router-dom";
import {
  ClientProjectApiError,
  type ClientProject,
  type ClientSession,
  clientDownloadHeaders,
  clientProjectReportDownloadUrl,
  clientRecordingDownloadUrl,
  clientTranscriptDownloadUrl,
  fetchClientProject,
  fetchClientProjectSessions,
} from "../lib/clientProjectApi";
import { downloadFile } from "../lib/researchApi";
import {
  clearClientProjectGrant,
  loadClientProjectGrant,
} from "../lib/clientProjectGrant";

const STATUS_LABEL: Record<ClientSession["status"], string> = {
  created: "준비 중",
  running: "진행 중",
  ended: "종료됨",
};

function formatSessionReference(id: string): string {
  const parts = id.split("_");
  if (parts.length > 1) {
    return `#${parts[1]}`;
  }
  return `#${id}`;
}

export default function ClientProject() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const grant = loadClientProjectGrant();
  const [project, setProject] = useState<ClientProject | null>(null);
  const [sessions, setSessions] = useState<ClientSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  /** 진행 중인 다운로드 키 (버튼 중복 클릭 방지) */
  const [busyDownload, setBusyDownload] = useState("");
  const [downloadError, setDownloadError] = useState("");

  const runDownload = async (key: string, url: string) => {
    if (!grant) return;
    setBusyDownload(key);
    setDownloadError("");
    try {
      await downloadFile(url, clientDownloadHeaders(grant.accessToken));
    } catch (cause: unknown) {
      setDownloadError(
        cause instanceof Error ? cause.message : "다운로드에 실패했습니다.",
      );
    } finally {
      setBusyDownload("");
    }
  };

  const loadData = async (isManualRefresh = false) => {
    if (!projectId || !grant || grant.projectId !== projectId) return;
    if (isManualRefresh) setRefreshing(true);
    try {
      const [loadedProject, loadedSessions] = await Promise.all([
        fetchClientProject(projectId, grant.accessToken),
        fetchClientProjectSessions(projectId, grant.accessToken),
      ]);
      setProject(loadedProject);
      setSessions(loadedSessions);
      setError("");
    } catch (cause: unknown) {
      if (cause instanceof ClientProjectApiError && [401, 403, 404].includes(cause.status)) {
        clearClientProjectGrant();
        setError("프로젝트 접속 권한이 없거나 만료되었습니다.");
        return;
      }
      setError("프로젝트 정보를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
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
      <main className="client-project-shell">
        <section className="client-project-message-box">
          <ShieldCheck size={36} weight="duotone" color="#2997ff" />
          <h2>{error}</h2>
          <button type="button" className="client-btn-primary" onClick={returnToAccess}>
            Project Access ID 다시 입력
          </button>
        </section>
      </main>
    );
  }

  const runningCount = sessions.filter((s) => s.status === "running").length;
  const completedCount = sessions.filter((s) => s.status === "ended").length;

  return (
    <div className="client-portal-wrapper">
      {/* 상단바: 대시보드 스타일 탑바 */}
      <header className="client-topbar">
        <div className="client-topbar-left">
          <span className="client-glyph">AI</span>
          <span className="client-brand-title">참관자 백룸 · 세션 목록</span>
          {project && (
            <span className="client-project-chip">
              <Lock size={12} weight="bold" /> {project.access_id || project.id}
            </span>
          )}
        </div>
        <div className="client-topbar-right">
          <button
            type="button"
            className="client-btn-ghost"
            onClick={() => loadData(true)}
            disabled={refreshing}
            title="새로고침"
          >
            <ArrowsClockwise size={15} className={refreshing ? "spin-icon" : ""} /> 새로고침
          </button>
          <button type="button" className="client-btn-ghost danger" onClick={returnToAccess}>
            <SignOut size={15} /> 다른 프로젝트 접속
          </button>
        </div>
      </header>

      {/* 메인 대시보드 세션 목록 패널 */}
      <main className="client-main-content">
        <div className="client-session-panel">
          <div className="client-panel-header">
            <div>
              <h2>세션 목록</h2>
              <div className="client-panel-sub">
                의뢰하신 프로젝트의 실시간 인터뷰 진행 현황 및 참관자 백룸 목록입니다.
              </div>
            </div>
            {project && (
              <div className="client-stat-chips">
                <span className="stat-chip">전체 {sessions.length}</span>
                {runningCount > 0 && <span className="stat-chip running">진행 중 {runningCount}</span>}
                <span className="stat-chip completed">완료 {completedCount}</span>
              </div>
            )}
          </div>

          <div className="client-panel-body">
            {/* 프로젝트 고정 안내 영역 (변경 불가) */}
            <div className="client-project-locked-card">
              <div className="locked-card-label">
                <span>프로젝트 (고정됨)</span>
                <span className="locked-badge"><Lock size={11} weight="fill" /> 변경 불가</span>
              </div>
              <div className="locked-card-title">
                {project ? project.title : "불러오는 중..."}
              </div>
              {project?.research_purpose && (
                <div className="locked-card-purpose">
                  <FileText size={14} weight="duotone" /> {project.research_purpose}
                </div>
              )}
            </div>

            {/* 프로젝트 단위 리포트 다운로드 */}
            <div className="client-report-card">
              <div className="report-card-info">
                <span className="report-card-icon"><FileDoc size={18} weight="duotone" /></span>
                <div>
                  <strong>프로젝트 종합 리포트</strong>
                  <small>완료된 인터뷰 {completedCount}건 기준 · PM이 생성한 최신본</small>
                </div>
              </div>
              <button
                type="button"
                className="session-download-btn primary"
                disabled={busyDownload === "report"}
                onClick={() =>
                  void runDownload("report", clientProjectReportDownloadUrl(projectId))
                }
              >
                <DownloadSimple size={14} weight="bold" />
                {busyDownload === "report" ? "받는 중…" : "리포트 다운로드"}
              </button>
            </div>

            {downloadError && (
              <p className="client-download-error" role="alert">
                <Warning size={14} weight="fill" /> {downloadError}
              </p>
            )}

            {/* 세션 목록 영역 */}
            <div className="client-session-list-section">
              <div className="session-section-title">
                <span>인터뷰 세션 목록</span>
              </div>

              {loading && <p className="client-muted-text">세션 목록을 불러오는 중입니다…</p>}

              {!loading && sessions.length === 0 && (
                <div className="client-empty-box">
                  <Clock size={32} weight="duotone" />
                  <p>이 프로젝트엔 아직 생성된 인터뷰 세션이 없습니다.</p>
                  <span>인터뷰어가 세션을 생성하면 여기에 실시간으로 표시됩니다.</span>
                </div>
              )}

              <div className="client-session-rows">
                {sessions.map((session) => {
                  const isRunning = session.status === "running";
                  const isEnded = session.status === "ended";

                  return (
                    <div key={session.id} className={`client-session-row ${session.status}`}>
                      <div className="session-row-info">
                        <div className="session-status-badge-wrap">
                          <span className={`client-badge ${session.status}`}>
                            {isRunning && <span className="pulse-dot" />}
                            {STATUS_LABEL[session.status]}
                          </span>
                          {/* PM이 입력한 참가자 ID를 그대로 보여준다. 비어 있는 예전 세션만
                              내부 ID 축약값으로 폴백한다. */}
                          <strong className="session-participant">
                            {session.title?.trim() || formatSessionReference(session.id)}
                          </strong>
                        </div>
                        <div className="session-meta">
                          <span>생성: {new Date(session.created_at).toLocaleString("ko-KR")}</span>
                          <span>·</span>
                          <span>예정 시간: {session.duration_minutes}분</span>
                        </div>
                      </div>

                      <div className="session-row-action">
                        <a
                          // 클라이언트 토큰을 함께 넘겨야 백룸이 '참관 전용'으로 열린다.
                          // 이 토큰이 없으면 백엔드가 PM 연결로 취급해 지시 권한이 열린다.
                          href={`/dashboard/?session=${encodeURIComponent(session.id)}&client_token=${encodeURIComponent(grant.accessToken)}`}
                          className={`client-enter-btn ${isRunning ? "running" : isEnded ? "ended" : "created"}`}
                        >
                          {isRunning ? (
                            <>
                              <span className="live-indicator">🔴</span> 실시간 백룸 입장 →
                            </>
                          ) : isEnded ? (
                            <>
                              <FileText size={15} /> 인터뷰 리포트 확인 →
                            </>
                          ) : (
                            <>
                              <PlayCircle size={15} /> 백룸 대기실 입장 →
                            </>
                          )}
                        </a>

                        {/* 완료된 인터뷰만 기록·영상이 확정된다 */}
                        {isEnded && (
                          <div className="session-download-row">
                            <button
                              type="button"
                              className="session-download-btn"
                              disabled={busyDownload === `t-${session.id}`}
                              onClick={() =>
                                void runDownload(
                                  `t-${session.id}`,
                                  clientTranscriptDownloadUrl(projectId!, session.id),
                                )
                              }
                            >
                              <FileText size={14} />
                              {busyDownload === `t-${session.id}` ? "받는 중…" : "질문·답변 기록"}
                            </button>
                            <button
                              type="button"
                              className="session-download-btn"
                              disabled={busyDownload === `v-${session.id}`}
                              onClick={() =>
                                void runDownload(
                                  `v-${session.id}`,
                                  clientRecordingDownloadUrl(projectId!, session.id),
                                )
                              }
                            >
                              <VideoCamera size={14} />
                              {busyDownload === `v-${session.id}` ? "받는 중…" : "녹화 영상"}
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        <p className="client-security-footer">
          <ShieldCheck size={16} weight="fill" />
          입력하신 Project Access ID와 연결된 전용 공간입니다.
        </p>
      </main>

      <style>{`
        .client-portal-wrapper {
          min-height: 100vh;
          background: #0b0f19;
          color: #e2e8f0;
          font-family: Pretendard, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        .client-topbar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          height: 60px;
          padding: 0 24px;
          background: #111827;
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
          position: sticky;
          top: 0;
          z-index: 50;
        }

        .client-topbar-left {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .client-glyph {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 28px;
          height: 28px;
          border-radius: 6px;
          background: linear-gradient(135deg, #3b82f6, #6366f1);
          color: #ffffff;
          font-size: 12px;
          font-weight: 800;
          letter-spacing: -0.05em;
        }

        .client-brand-title {
          font-size: 15px;
          font-weight: 700;
          color: #f8fafc;
          letter-spacing: -0.02em;
        }

        .client-project-chip {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          padding: 4px 10px;
          background: rgba(59, 130, 246, 0.12);
          border: 1px solid rgba(59, 130, 246, 0.3);
          border-radius: 999px;
          font-size: 12px;
          font-weight: 600;
          color: #60a5fa;
        }

        .client-topbar-right {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .client-btn-ghost {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 7px 12px;
          background: transparent;
          border: 1px solid rgba(255, 255, 255, 0.12);
          border-radius: 6px;
          color: #cbd5e1;
          font-size: 13px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .client-btn-ghost:hover:not(:disabled) {
          background: rgba(255, 255, 255, 0.06);
          color: #ffffff;
        }

        .client-btn-ghost.danger:hover {
          background: rgba(239, 68, 68, 0.12);
          border-color: rgba(239, 68, 68, 0.3);
          color: #f87171;
        }

        .spin-icon {
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          100% { transform: rotate(360deg); }
        }

        .client-main-content {
          max-width: 860px;
          margin: 40px auto;
          padding: 0 20px;
        }

        .client-session-panel {
          background: #1e293b;
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 16px;
          box-shadow: 0 20px 40px rgba(0, 0, 0, 0.35);
          overflow: hidden;
        }

        .client-panel-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 24px 28px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
          background: rgba(15, 23, 42, 0.5);
        }

        .client-panel-header h2 {
          margin: 0;
          font-size: 20px;
          font-weight: 700;
          color: #f8fafc;
          letter-spacing: -0.02em;
        }

        .client-panel-sub {
          margin-top: 6px;
          font-size: 13px;
          color: #94a3b8;
        }

        .client-stat-chips {
          display: flex;
          gap: 8px;
        }

        .stat-chip {
          padding: 4px 10px;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.06);
          border: 1px solid rgba(255, 255, 255, 0.1);
          font-size: 12px;
          font-weight: 600;
          color: #cbd5e1;
        }

        .stat-chip.running {
          background: rgba(16, 185, 129, 0.15);
          border-color: rgba(16, 185, 129, 0.35);
          color: #34d399;
        }

        .stat-chip.completed {
          background: rgba(100, 116, 139, 0.2);
          color: #94a3b8;
        }

        .client-panel-body {
          padding: 28px;
        }

        .client-project-locked-card {
          padding: 16px 20px;
          background: rgba(15, 23, 42, 0.6);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 12px;
          margin-bottom: 24px;
        }

        .locked-card-label {
          display: flex;
          align-items: center;
          justify-content: space-between;
          font-size: 12px;
          font-weight: 600;
          color: #94a3b8;
          margin-bottom: 8px;
        }

        .locked-badge {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 2px 7px;
          background: rgba(255, 255, 255, 0.06);
          border-radius: 4px;
          font-size: 10px;
          color: #94a3b8;
        }

        .locked-card-title {
          font-size: 17px;
          font-weight: 700;
          color: #f1f5f9;
          letter-spacing: -0.01em;
        }

        .locked-card-purpose {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-top: 8px;
          font-size: 13px;
          color: #60a5fa;
        }

        .client-session-list-section {
          margin-top: 10px;
        }

        .session-section-title {
          font-size: 14px;
          font-weight: 600;
          color: #cbd5e1;
          margin-bottom: 14px;
        }

        .client-muted-text {
          font-size: 13px;
          color: #94a3b8;
          padding: 16px 0;
        }

        .client-empty-box {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 48px 24px;
          background: rgba(15, 23, 42, 0.3);
          border: 1px dashed rgba(255, 255, 255, 0.12);
          border-radius: 12px;
          text-align: center;
          color: #94a3b8;
        }

        .client-empty-box p {
          margin: 12px 0 4px;
          font-size: 15px;
          font-weight: 600;
          color: #e2e8f0;
        }

        .client-empty-box span {
          font-size: 13px;
          color: #64748b;
        }

        .client-session-rows {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .client-session-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 16px 20px;
          background: rgba(15, 23, 42, 0.45);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 12px;
          transition: all 0.18s ease;
        }

        .client-session-row:hover {
          background: rgba(15, 23, 42, 0.7);
          border-color: rgba(59, 130, 246, 0.35);
          transform: translateY(-1px);
        }

        .client-session-row.running {
          border-color: rgba(16, 185, 129, 0.35);
          background: rgba(16, 185, 129, 0.05);
        }

        .session-row-info {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .session-status-badge-wrap {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .client-badge {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 3px 8px;
          border-radius: 999px;
          font-size: 11px;
          font-weight: 700;
        }

        .client-badge.running {
          background: rgba(16, 185, 129, 0.2);
          color: #34d399;
          border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .client-badge.created {
          background: rgba(59, 130, 246, 0.2);
          color: #60a5fa;
          border: 1px solid rgba(59, 130, 246, 0.3);
        }

        .client-badge.ended {
          background: rgba(100, 116, 139, 0.2);
          color: #94a3b8;
          border: 1px solid rgba(100, 116, 139, 0.3);
        }

        .pulse-dot {
          width: 7px;
          height: 7px;
          border-radius: 50%;
          background: #10b981;
          box-shadow: 0 0 8px #10b981;
          animation: badge-pulse 1.8s infinite;
        }

        @keyframes badge-pulse {
          0% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.4; transform: scale(0.85); }
          100% { opacity: 1; transform: scale(1); }
        }

        .session-ref {
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
          font-size: 13px;
          font-weight: 600;
          color: #f1f5f9;
        }

        /* PM이 입력한 참가자 ID — 세션 목록에서 누구의 인터뷰인지 식별하는 값 */
        .session-participant {
          font-size: 14px;
          font-weight: 650;
          color: #f1f5f9;
          letter-spacing: -0.01em;
        }

        /* 프로젝트 리포트 / 인터뷰 자료 다운로드 */
        .client-report-card {
          display: flex;
          flex-wrap: wrap;
          gap: 14px;
          align-items: center;
          justify-content: space-between;
          margin: 18px 0 6px;
          padding: 18px 20px;
          border: 1px solid rgba(148, 163, 184, 0.22);
          border-radius: 14px;
          background: rgba(30, 41, 59, 0.5);
        }

        .report-card-info {
          display: grid;
          grid-template-columns: 38px minmax(0, 1fr);
          gap: 12px;
          align-items: center;
        }

        .report-card-icon {
          display: grid;
          width: 36px;
          height: 36px;
          place-items: center;
          border-radius: 11px;
          background: rgba(59, 130, 246, 0.16);
          color: #60a5fa;
        }

        .report-card-info strong {
          display: block;
          font-size: 14px;
          color: #f1f5f9;
        }

        .report-card-info small {
          display: block;
          margin-top: 3px;
          font-size: 12px;
          color: #94a3b8;
        }

        .session-download-row {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-top: 8px;
        }

        .session-download-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 7px 12px;
          border: 1px solid rgba(148, 163, 184, 0.32);
          border-radius: 999px;
          background: transparent;
          color: #cbd5e1;
          font-family: inherit;
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
          white-space: nowrap;
        }

        .session-download-btn:hover:not(:disabled) {
          border-color: #60a5fa;
          color: #93c5fd;
        }

        .session-download-btn:disabled {
          opacity: 0.45;
          cursor: not-allowed;
        }

        .session-download-btn.primary {
          border-color: transparent;
          background: #2563eb;
          color: #fff;
        }

        .session-download-btn.primary:hover:not(:disabled) {
          background: #1d4ed8;
          color: #fff;
        }

        .client-download-error {
          display: flex;
          align-items: center;
          gap: 7px;
          margin: 10px 0 0;
          padding: 9px 13px;
          border: 1px solid rgba(239, 68, 68, 0.35);
          border-radius: 11px;
          background: rgba(239, 68, 68, 0.1);
          color: #fca5a5;
          font-size: 12.5px;
        }

        .session-meta {
          font-size: 12px;
          color: #64748b;
          display: flex;
          gap: 6px;
        }

        .client-enter-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 8px 16px;
          border-radius: 8px;
          font-size: 13px;
          font-weight: 600;
          text-decoration: none;
          transition: all 0.15s ease;
          white-space: nowrap;
        }

        .client-enter-btn.running {
          background: #10b981;
          color: #ffffff;
          box-shadow: 0 0 14px rgba(16, 185, 129, 0.4);
        }

        .client-enter-btn.running:hover {
          background: #059669;
          transform: scale(1.02);
        }

        .client-enter-btn.created {
          background: #3b82f6;
          color: #ffffff;
        }

        .client-enter-btn.created:hover {
          background: #2563eb;
        }

        .client-enter-btn.ended {
          background: rgba(255, 255, 255, 0.08);
          border: 1px solid rgba(255, 255, 255, 0.12);
          color: #cbd5e1;
        }

        .client-enter-btn.ended:hover {
          background: rgba(255, 255, 255, 0.15);
          color: #ffffff;
        }

        .live-indicator {
          font-size: 10px;
          animation: blink 1s infinite;
        }

        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }

        .client-security-footer {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 7px;
          margin-top: 24px;
          font-size: 12px;
          color: #64748b;
        }

        .client-project-shell {
          display: grid;
          min-height: 100vh;
          place-items: center;
          background: #0b0f19;
          padding: 20px;
        }

        .client-project-message-box {
          display: flex;
          flex-direction: column;
          align-items: center;
          text-align: center;
          padding: 40px;
          background: #1e293b;
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 16px;
          max-width: 440px;
          width: 100%;
        }

        .client-project-message-box h2 {
          margin: 16px 0 24px;
          font-size: 17px;
          font-weight: 600;
          color: #f1f5f9;
        }

        .client-btn-primary {
          padding: 10px 20px;
          background: #3b82f6;
          border: 0;
          border-radius: 8px;
          color: #ffffff;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
        }
      `}</style>
    </div>
  );
}
