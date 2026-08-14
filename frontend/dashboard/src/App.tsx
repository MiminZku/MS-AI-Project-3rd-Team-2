import { useState } from "react";
import Monitor, { type TopbarStatus } from "./components/Monitor";
import SessionForm from "./components/SessionForm";

export type Role = "pm" | "client";

/**
 * 참관자 대시보드.
 *
 * TODO(MVP): 관리자 로그인. Static Web Apps 인증(Entra ID)을 붙이고
 * 여기서 /.auth/me 를 확인하도록 교체한다. 지금은 VITE_ADMIN_TOKEN 기반 데모.
 */
export default function App() {
  const [sessionId, setSessionId] = useState<string>(
    () => new URLSearchParams(window.location.search).get("session") ?? "",
  );
  const [intervieweeUrl, setIntervieweeUrl] = useState("");
  const [role, setRole] = useState<Role>("pm");
  const [topbarStatus, setTopbarStatus] = useState<TopbarStatus | null>(null);

  return (
    <div>
      <header className="topbar">
        <div className="crumb">
          <span className="glyph">AI</span>참관자 대시보드
        </div>
        <div className="top-right">
          {sessionId && (
            <div className="role-switch">
              <button className={role === "pm" ? "on" : ""} onClick={() => setRole("pm")}>
                PM 모드
              </button>
              <button className={role === "client" ? "on" : ""} onClick={() => setRole("client")}>
                클라이언트 모드
              </button>
            </div>
          )}
          <span className="role-chip">{role === "pm" ? "PM · Observer" : "클라이언트 · Observer"}</span>

          {topbarStatus && (
            <>
              <span className="timer">
                <span className="dot" />
                <b>{topbarStatus.timerLabel}</b>
                <small>{topbarStatus.phaseLabel}</small>
              </span>
              <span className={`badge ${topbarStatus.connectionStatus}`}>{topbarStatus.connectionStatus}</span>
              {topbarStatus.role === "pm" && (topbarStatus.phase === "wait" || topbarStatus.phase === "joined") && (
                <button className="sess-btn go" disabled title="곧 지원 예정 · 지금은 응답자 접속 시 자동 시작됩니다">
                  인터뷰 시작
                </button>
              )}
              {topbarStatus.role === "pm" && (topbarStatus.phase === "joined" || topbarStatus.phase === "live") && (
                <button className="sess-btn go" disabled title="곧 지원 예정 · 영상 녹화 파이프라인 구축 후 연동">
                  녹화 시작
                </button>
              )}
              {topbarStatus.role === "pm" && topbarStatus.phase === "end" && (
                <button className="sess-btn go" disabled={!topbarStatus.hasReport} onClick={topbarStatus.onOpenReport}>
                  {topbarStatus.hasReport ? "리포트 열기" : "리포트 생성 중…"}
                </button>
              )}
              {topbarStatus.role === "pm" && topbarStatus.phase === "live" && (
                <button className="sess-btn stop" disabled={topbarStatus.ending} onClick={topbarStatus.onEndSession}>
                  인터뷰 종료
                </button>
              )}
            </>
          )}

          {sessionId && (
            <button
              className="ghost"
              onClick={() => {
                setSessionId("");
                setIntervieweeUrl("");
              }}
            >
              세션 목록으로
            </button>
          )}
        </div>
      </header>

      {sessionId ? (
        <Monitor sessionId={sessionId} intervieweeUrl={intervieweeUrl} role={role} onStatusChange={setTopbarStatus} />
      ) : (
        <SessionForm
          onCreated={(session, url) => {
            setSessionId(session.id);
            setIntervieweeUrl(url);
          }}
        />
      )}
    </div>
  );
}
