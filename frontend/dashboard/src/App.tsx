import { useState } from "react";
import Monitor, { type TopbarStatus } from "./components/Monitor";
import SessionForm from "./components/SessionForm";

export type Role = "pm";

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
  // Client는 web 앱의 Project Access ID 전용 화면으로만 접근한다.
  // 대시보드는 PM 운영 화면이므로 URL query로 역할을 바꿀 수 없다.
  const role: Role = "pm";
  const [topbarStatus, setTopbarStatus] = useState<TopbarStatus | null>(null);

  return (
    <div>
      <header className="topbar">
        <div className="crumb">
          <span className="glyph">AI</span>참관자 대시보드
        </div>
        <div className="top-right">
          {topbarStatus && (
            <>
              {topbarStatus.role === "pm" && (topbarStatus.phase === "wait" || topbarStatus.phase === "joined") && (
                <button
                  className="sess-btn go"
                  disabled={topbarStatus.starting}
                  onClick={topbarStatus.onStartSession}
                >
                  {topbarStatus.starting ? "시작 중..." : "인터뷰 시작"}
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
          role={role}
          onCreated={(session, url) => {
            setSessionId(session.id);
            setIntervieweeUrl(url);
          }}
        />
      )}
    </div>
  );
}
