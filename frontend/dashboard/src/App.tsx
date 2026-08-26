import { useState } from "react";
import { ErrorBoundary } from "./components/ErrorBoundary";
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
  // 클라이언트는 web 앱의 Project Access ID 화면에서 발급받은 토큰을 달고 들어온다.
  // 토큰이 있으면 참관 전용(client)이고, 실시간 지시를 보낼 수 없다.
  // 토큰 유효성은 백엔드가 소켓 연결 시 다시 검증하므로, 여기서 역할을 위조해도 지시는 거부된다.
  const clientToken = new URLSearchParams(window.location.search).get("client_token") ?? "";
  const role: Role = clientToken ? "client" : "pm";
  const [topbarStatus, setTopbarStatus] = useState<TopbarStatus | null>(null);

  return (
    <ErrorBoundary>
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
        <Monitor
          sessionId={sessionId}
          intervieweeUrl={intervieweeUrl}
          role={role}
          clientToken={clientToken}
          onStatusChange={setTopbarStatus}
        />
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
    </ErrorBoundary>
  );
}
