import { useState } from "react";
import Monitor from "./components/Monitor";
import SessionForm from "./components/SessionForm";

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

  return (
    <div className="app">
      <header className="topbar">
        <h1>참관자 대시보드</h1>
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
      </header>

      {sessionId ? (
        <Monitor sessionId={sessionId} intervieweeUrl={intervieweeUrl} />
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
