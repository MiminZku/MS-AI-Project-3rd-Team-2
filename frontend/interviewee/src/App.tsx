import { useEffect, useRef, useState } from "react";
import { WS_BASE_URL, sessionIdFromUrl } from "./config";
import type { ServerMessage, Turn } from "./types";
import WaitingScreen from "./components/WaitingScreen";
import TranscriptHistory from "./components/TranscriptHistory";
import Orb from "./components/Orb";

type Status = "idle" | "connecting" | "connected" | "closed" | "error";
type SessionStatus = "created" | "running" | "ended";
type EntryStep = "gromit" | "welcome_code" | "media_setup" | "consent" | "waiting" | "running" | "ended";

export default function App() {
  const [sessionId] = useState(sessionIdFromUrl);
  const [status, setStatus] = useState<Status>("idle");
  const [sessionStatus, setSessionStatus] = useState<SessionStatus>("created");
  const [entryStep, setEntryStep] = useState<EntryStep>("gromit");

  // Flow states
  const [enteredCode, setEnteredCode] = useState("");
  const [micOn, setMicOn] = useState(false);
  const [camOn, setCamOn] = useState(false);
  const [isAgreedToRecord, setIsAgreedToRecord] = useState(false);
  const [isAgreedToPrivacy, setIsAgreedToPrivacy] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const [title, setTitle] = useState("");
  const [question, setQuestion] = useState("대화 상대를 기다리고 있습니다.");
  const [history, setHistory] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [orbState, setOrbState] = useState<"idle" | "speaking" | "listening">("idle");
  const socketRef = useRef<WebSocket | null>(null);

  // 1. Splash screen timer: Transition from 'gromit' to 'welcome_code' after 5s
  useEffect(() => {
    if (entryStep === "gromit") {
      const timer = setTimeout(() => {
        setEntryStep("welcome_code");
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [entryStep]);

  // 2. WebSocket Connection: Connect immediately if sessionId is available
  useEffect(() => {
    if (!sessionId) return;

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
      } else if (message.type === "assistant.question") {
        setQuestion(message.turn.text);
        setHistory((prev) => [...prev, message.turn]);
        setOrbState("speaking");

        // Simulation: switch to listening mode after AI finishes speaking
        setTimeout(() => {
          setOrbState("listening");
        }, 3000);
      } else if (message.type === "error") {
        setQuestion(`오류: ${message.message}`);
        setOrbState("idle");
      }
    };

    return () => socket.close();
  }, [sessionId]);

  // 3. Handle transition to 'running' room when waiting and session is running
  useEffect(() => {
    if (entryStep === "waiting" && sessionStatus === "running") {
      setEntryStep("running");
      setOrbState("idle");
    }
  }, [entryStep, sessionStatus]);

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

  const handleCodeSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!enteredCode.trim()) {
      setErrorMessage("입장 코드를 입력해 주세요.");
      return;
    }
    setErrorMessage("");
    setEntryStep("media_setup");
  };

  const handleMediaSubmit = () => {
    setEntryStep("consent");
  };

  const handleConsentSubmit = () => {
    if (!isAgreedToRecord || !isAgreedToPrivacy) {
      setErrorMessage("모든 필수 항목에 동의해 주세요.");
      return;
    }
    setErrorMessage("");
    setEntryStep("waiting");
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

  // Step 1: Gromit Screen
  if (entryStep === "gromit") {
    return (
      <main className="landing-gromit">
        <div className="gromit-text">Gromit</div>
      </main>
    );
  }

  // Step 2: Welcome and Entry Code Input
  if (entryStep === "welcome_code") {
    return (
      <main className="shell">
        <div className="landing-welcome-container">
          <h1 className="welcome-title">
            {title ? `"${title}"에 온 것을 환영합니다` : "인터뷰에 온 것을 환영합니다"}
          </h1>

          <form className="code-input-panel" onSubmit={handleCodeSubmit}>
            <div className="input-group">
              <label style={{ fontSize: 14, color: "var(--muted)" }}>인터뷰 입장 코드 입력</label>
              <input
                type="text"
                className="text-input-premium"
                placeholder="입장 코드를 입력하세요"
                value={enteredCode}
                onChange={(e) => setEnteredCode(e.target.value)}
              />
              {errorMessage && <p style={{ color: "var(--error)", fontSize: 13, margin: "4px 0" }}>{errorMessage}</p>}
              <button type="submit" className="btn-primary">입장하기</button>
            </div>
          </form>
        </div>
      </main>
    );
  }

  // Step 3: Media Setup
  if (entryStep === "media_setup") {
    return (
      <main className="shell">
        <div className="media-setup-container">
          <h1 className="welcome-title" style={{ marginBottom: 40 }}>인터뷰 시작 전 장치 설정</h1>

          <div className="code-input-panel" style={{ margin: "0 auto 32px" }}>
            <div className="toggle-card">
              <span className="toggle-label">🎤 마이크</span>
              <button
                className={`toggle-switch-btn ${micOn ? "on" : "off"}`}
                onClick={() => setMicOn(!micOn)}
              >
                {micOn ? "ON" : "OFF"}
              </button>
            </div>

            <div className="toggle-card">
              <span className="toggle-label">📷 카메라</span>
              <button
                className={`toggle-switch-btn ${camOn ? "on" : "off"}`}
                onClick={() => setCamOn(!camOn)}
              >
                {camOn ? "ON" : "OFF"}
              </button>
            </div>
          </div>

          <div style={{ display: "flex", gap: "16px", marginTop: "24px" }}>
            <button className="btn-secondary" style={{ flex: 1 }} onClick={() => setEntryStep("welcome_code")}>
              이전
            </button>
            <button className="btn-primary" style={{ flex: 1 }} onClick={handleMediaSubmit}>
              다음
            </button>
          </div>
        </div>
      </main>
    );
  }

  // Step 4: Pre-Interview Instructions and Consent
  if (entryStep === "consent") {
    return (
      <main className="shell">
        <section className="glass-panel">
          <h2 style={{ color: "var(--text-white)", marginTop: 0 }}>🎙️ 인터뷰 사전 안내 및 동의</h2>
          <p className="muted" style={{ marginBottom: 20 }}>
            원활한 AI 인터뷰 진행 및 데이터 저장을 위해 아래 안내 사항을 확인한 후 동의해 주시기 바랍니다.
          </p>

          <div className="consent-scroll-box">
            <h3>※ 이 인터뷰는 AI 모더레이터가 진행합니다</h3>
            <p>
              사람이 아닌 AI가 실시간으로 질문하고 대화를 이어갑니다. AI 진행 특성상 답변 사이의 호흡이나 자연스러운 맞장구 등에서 사람 진행자와 다르게 다소 매끄럽지 못하게 느껴지는 순간이 있을 수 있습니다. 이는 정상적인 진행 방식이니 편하게 답변해 주시면 됩니다.
            </p>

            <h3>1. 조사 소개</h3>
            <p>
              귀하는 본 조사의 목적에 적합하여 초대되었습니다. AI 모더레이터와의 대화를 통해 진행되며, 실시간 AI 동시통역을 통해 조사를 의뢰한 클라이언트 측에도 대화 내용이 전달됩니다.
            </p>

            <h3>2. 인터뷰 관찰 및 열람 주체</h3>
            <ul>
              <li>AI 모더레이터가 실시간 진행을 담당합니다.</li>
              <li>리서치팀(내부 조사 인력)과 조사를 의뢰한 클라이언트 측 담당자(PM)가 별도 백룸에서 실시간 참관할 수 있습니다.</li>
              <li>클라이언트 담당자는 AI 동시통역을 통해 대화를 확인하며, 진행 중 참고할 질문을 리서치팀에 전달할 수 있습니다.</li>
              <li>녹음·녹취본은 리서치팀과 클라이언트 조사 담당자만 열람하며, 외부에 공유되지 않습니다.</li>
            </ul>

            <h3>3. 수집하는 정보와 이용 목적</h3>
            <ul>
              <li>수집 항목: 인터뷰 중 답변 내용(음성/텍스트) 및 녹음·녹취 데이터</li>
              <li>이용 목적: 조사 분석 및 클라이언트 보고 목적으로만 사용되며, 수집된 데이터는 AI 모델 학습(훈련) 목적으로는 사용되지 않습니다.</li>
              <li>보관 기간: 조사 종료 후 프로젝트 보고 완료 시점까지, 또는 계약상 별도 합의된 기간</li>
            </ul>

            <h3>4. 답변 시 유의사항</h3>
            <p>
              인터뷰 중 주민등록번호, 계좌번호, 비밀번호 등 개인 식별이 가능한 민감 정보는 언급하지 말아 주세요. 응답자가 자발적으로 언급한 민감 정보에 대해서는 당사가 책임지지 않습니다.
            </p>

            <h3>5. 참여자의 권리</h3>
            <p>
              인터뷰 도중 언제든 답변을 거부하거나 참여를 중단할 수 있습니다. 중단하셔도 불이익은 없습니다.
            </p>

            <h3>6. 문의</h3>
            <p>
              문의사항이 있으신 경우 contactus@gromit.ai 로 연락 주시기 바랍니다.
            </p>
          </div>

          <div className="agree-block">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={isAgreedToRecord}
                onChange={(e) => setIsAgreedToRecord(e.target.checked)}
              />
              <span>(필수) 인터뷰 진행 시 오디오/비디오 녹화 및 기록에 동의합니다.</span>
            </label>

            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={isAgreedToPrivacy}
                onChange={(e) => setIsAgreedToPrivacy(e.target.checked)}
              />
              <span>(필수) 인터뷰 데이터 분석을 위한 개인정보 처리방침에 동의합니다.</span>
            </label>
          </div>

          {errorMessage && <p className="error-alert">{errorMessage}</p>}

          <div style={{ display: "flex", gap: "16px", marginTop: "24px" }}>
            <button className="btn-secondary" style={{ flex: 1 }} onClick={() => setEntryStep("media_setup")}>
              이전
            </button>
            <button className="btn-primary" style={{ flex: 1 }} onClick={handleConsentSubmit} disabled={!isAgreedToRecord || !isAgreedToPrivacy}>
              다음
            </button>
          </div>
        </section>
      </main>
    );
  }

  // Step 5: Waiting room
  if (entryStep === "waiting") {
    return (
      <main className="shell">
        <WaitingScreen title={title || "AI 인터뷰 대기실"} />
        <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginTop: "24px", alignItems: "center" }}>
          <button className="btn-secondary" onClick={() => setEntryStep("consent")}>
            이전 단계 (동의 재설정)
          </button>

          {sessionId === "default-session" && (
            <button className="btn-secondary" onClick={() => { setSessionStatus("running"); setEntryStep("running"); setStatus("connected"); }}>
              [개발자용] 인터뷰 시작 테스트 (running 상태 전환)
            </button>
          )}
        </div>
      </main>
    );
  }

  // Step 6: Ended or Closed
  if (entryStep === "ended" || sessionStatus === "ended" || status === "closed") {
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
            <button className="btn-secondary" onClick={() => { setSessionStatus("running"); setEntryStep("running"); setStatus("connected"); }}>
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
      <header className="main-header">
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


