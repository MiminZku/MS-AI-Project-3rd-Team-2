import { useState } from "react";
import Monitor from "./components/Monitor";
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
        <Monitor sessionId={sessionId} intervieweeUrl={intervieweeUrl} role={role} />
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
