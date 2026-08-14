import { useEffect, useRef, useState } from "react";
import { WS_BASE_URL, sessionIdFromUrl } from "./config";
import type { ServerMessage, Turn } from "./types";
import PermissionGate from "./components/PermissionGate";
import WaitingScreen from "./components/WaitingScreen";
import TranscriptHistory from "./components/TranscriptHistory";
import Orb from "./components/Orb";

type Status = "idle" | "connecting" | "connected" | "closed" | "error";
type SessionStatus = "created" | "running" | "ended";

export default function App() {
  const [sessionId] = useState(sessionIdFromUrl);
  const [status, setStatus] = useState<Status>("idle");
  const [sessionStatus, setSessionStatus] = useState<SessionStatus>("created");
  const [isConsented, setIsConsented] = useState(false);
  const [title, setTitle] = useState("");
  const [question, setQuestion] = useState("대화 상대를 기다리고 있습니다.");
  const [history, setHistory] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [orbState, setOrbState] = useState<"idle" | "speaking" | "listening">("idle");
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!sessionId || !isConsented) return;

    setStatus("connecting");
    const socket = new WebSocket(`${WS_BASE_URL}/ws/interview/${sessionId}`);
    socketRef.current = socket;

    socket.onopen = () => setStatus("connected");
    socket.onclose = () => setStatus("closed");
    socket.onerror = () => setStatus("error");
    socket.onmessage = (event) => {
      const message: ServerMessage = JSON.parse(event.data);
      if (message.type === "session.state") {
        setTitle(message.session.title);
        setSessionStatus(message.session.status);
        if (message.session.status === "running") {
          setOrbState("idle");
        }
      } else if (message.type === "assistant.question") {
        setQuestion(message.turn.text);
        setHistory((prev) => [...prev, message.turn]);
        setOrbState("speaking");
        
        // 시뮬레이션: AI 발화 완료 후 듣기 모드로 전환 (실제 STT 탑재 전 연출)
        setTimeout(() => {
          setOrbState("listening");
        }, 3000);
      } else if (message.type === "error") {
        setQuestion(`오류: ${message.message}`);
        setOrbState("idle");
      }
    };

    return () => socket.close();
  }, [sessionId, isConsented]);

  const send = () => {
    const text = draft.trim();
    const socket = socketRef.current;
    if (!text || socket?.readyState !== WebSocket.OPEN) return;

    socket.send(JSON.stringify({ type: "utterance", text }));
    setHistory((prev) => [
      ...prev,
      {
        index: prev.length,
        speaker: "interviewee",
        text,
        created_at: new Date().toISOString(),
      },
    ]);
    setDraft("");
    setOrbState("idle");
  };

  if (!sessionId) {
    return (
      <main className="shell">
        <section className="glass-panel text-center">
          <h1>⚠️ 인터뷰 링크가 필요합니다</h1>
          <p className="muted">담당자가 보내드린 올바른 링크(?session=...)로 접속해 주세요.</p>
        </section>
      </main>
    );
  }

  // 1단계: 마이크/카메라 권한 및 동의 절차
  if (!isConsented) {
    return (
      <main className="shell">
        <PermissionGate onConsentComplete={() => setIsConsented(true)} />
      </main>
    );
  }

  // 2단계: 백엔드 상태가 created 인 경우 대기 화면 노출
  if (sessionStatus === "created") {
    return (
      <main className="shell">
        <WaitingScreen title={title} />
        {sessionId === "default-session" && (
          <div style={{ textAlign: "center", marginTop: 20 }}>
            <button className="btn-secondary" onClick={() => { setSessionStatus("running"); setStatus("connected"); }}>
              [개발자용] 인터뷰 시작 테스트 (running 상태 전환)
            </button>
          </div>
        )}
      </main>
    );
  }

  // 3단계: 종료 화면 분기
  if (sessionStatus === "ended" || status === "closed") {
    return (
      <main className="shell">
        <section className="glass-panel text-center">
          <h2>🎉 인터뷰이 최종 화면</h2>
          <p className="muted">
            성실하게 답변에 임해 주셔서 대단히 감사합니다.<br />
            이제 브라우저 창을 닫으셔도 좋습니다.
          </p>
        </section>
        {sessionId === "default-session" && (
          <div style={{ textAlign: "center", marginTop: 20 }}>
            <button className="btn-secondary" onClick={() => { setSessionStatus("running"); setStatus("connected"); }}>
              [개발자용] 다시 진행 화면으로
            </button>
          </div>
        )}
      </main>
    );
  }

  // 4단계: 정상 진행 화면
  return (
    <main className="shell">
      <header className="main-header glass-panel">
        <div className="title-area">
          <span className="live-dot" />
          <h1>{title || "AI 인터뷰"}</h1>
        </div>
        <span className={`badge-status ${status}`}>{status.toUpperCase()}</span>
      </header>

      <section className="stage-panel glass-panel">
        <Orb status={orbState} />
        <div className="question-box">
          <p className="question-bubble">{question}</p>
        </div>
      </section>

      <section className="composer-panel glass-panel">
        <div className="composer-wrapper">
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                send();
              }
            }}
            placeholder={orbState === "speaking" ? "AI 면접관의 질문이 끝나면 답변해 주세요..." : "질문에 대해 자세히 답변해 주세요..."}
            rows={3}
            disabled={status !== "connected" || orbState === "speaking"}
          />
          <button className="btn-send" onClick={send} disabled={status !== "connected" || !draft.trim() || orbState === "speaking"}>
            <span className="send-icon">📤</span> 전송
          </button>
        </div>
        <p className="composer-hint">
          {orbState === "speaking" ? "AI 가 질문을 읽는 중입니다." : "Enter를 누르면 답변이 전송됩니다. 줄바꿈은 Shift + Enter 입니다."}
        </p>
      </section>

      <TranscriptHistory history={history} />

      {sessionId === "default-session" && (
        <div style={{ textAlign: "center", marginTop: 20 }}>
          <button className="btn-secondary" onClick={() => setSessionStatus("ended")}>
            [개발자용] 종료 화면으로 강제 이동
          </button>
        </div>
      )}
    </main>
  );
}


