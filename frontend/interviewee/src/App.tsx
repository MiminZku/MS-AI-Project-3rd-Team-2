import { useEffect, useRef, useState } from "react";
import { WS_BASE_URL, sessionIdFromUrl } from "./config";
import type { ServerMessage, Turn } from "./types";
import WaitingScreen from "./components/WaitingScreen";
import PermissionExplainerModal from "./components/PermissionExplainerModal";
import { useAudioLevelMonitor } from "./hooks/useAudioLevelMonitor";
import AvatarMonitor from "./components/AvatarMonitor";
import RespondentMonitor from "./components/RespondentMonitor";
import QuestionPromptBox from "./components/QuestionPromptBox";
import VideoPublisher from "./components/VideoPublisher";
import { fetchRtcToken } from "./config";
import { useAvatarWebRTC } from "./hooks/useAvatarWebRTC";

type Status = "idle" | "connecting" | "connected" | "closed" | "error";
type SessionStatus = "created" | "running" | "ended";
type EntryStep = "gromit" | "welcome" | "consent" | "waiting" | "running" | "ended";

const DUMMY_QUESTIONS = [
  "평소 업무나 일상에서 AI 도구를 얼마나 자주 사용하시나요?",
  "주로 어떤 상황이나 업무에서 AI 도구가 가장 유용하다고 느끼셨나요?",
  "반대로 AI 도구를 사용하면서 아쉬웠거나 불편했던 점이 있으셨나요?",
  "마지막으로 앞으로 AI 인터뷰나 업무 도구에 바라는 점이 있다면 말씀해 주세요.",
];

const DUMMY_REACTIONS = [
  "아, 그러셨군요! 자세한 경험 공유 감사드립니다. 그렇다면...",
  "네, 충분히 공감되는 내용이네요. 그렇다면 이번에는...",
  "솔직하고 구체적인 의견 감사합니다! 많은 도움이 되었습니다. 마지막으로...",
];

export default function App() {
  const [sessionId] = useState(sessionIdFromUrl);
  const [status, setStatus] = useState<Status>("idle");
  // URL 파라미터에 test=avatar 가 있거나 빠른 테스트 지원
  const isDirectAvatarTest = new URLSearchParams(window.location.search).get("test") === "avatar";
  const [entryStep, setEntryStep] = useState<EntryStep>(isDirectAvatarTest ? "running" : "gromit");
  const [sessionStatus, setSessionStatus] = useState<SessionStatus>(isDirectAvatarTest ? "running" : "created");
  const [rtcCreds, setRtcCreds] = useState<{ token: string; group_id: string } | null>(null);

  // Flow states
  const [isRecording, setIsRecording] = useState(false);
  const [isChecking, setIsChecking] = useState(false);
  const [isExplainerOpen, setIsExplainerOpen] = useState(false);
  const [isAgreedToRecord, setIsAgreedToRecord] = useState(false);
  const [isAgreedToPrivacy, setIsAgreedToPrivacy] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const [title, setTitle] = useState(isDirectAvatarTest ? "AI 아바타 핑퐁 테스트" : "");
  const [dummyQuestionIndex, setDummyQuestionIndex] = useState(0);
  const [question, setQuestion] = useState(DUMMY_QUESTIONS[0]);
  const [speechSpeed, setSpeechSpeed] = useState<number>(1.35); // 기본 1.4x 빠름(추천)
  const [history, setHistory] = useState<Turn[]>([]);

  // Constant audio level monitor when on running step
  const isVoiceDetected = useAudioLevelMonitor(entryStep === "running");
  const showMicOffAlert = isVoiceDetected && !isRecording;

  const [orbState, setOrbState] = useState<"idle" | "speaking" | "listening">("idle");
  const socketRef = useRef<WebSocket | null>(null);

  // Azure Avatar WebRTC 훅 연동
  const avatar = useAvatarWebRTC({
    autoConnect: entryStep === "running",
    character: "lisa",
    voice: "ko-KR-SunHiNeural",
  });

  const speakWithCurrentSpeed = (text: string) => {
    avatar.speak(text, undefined, speechSpeed);
  };

  // 1. Splash screen timer: Transition from 'gromit' to 'welcome' after 3s (단독 테스트 모드가 아닐 때만)
  useEffect(() => {
    if (entryStep === "gromit") {
      const timer = setTimeout(() => {
        setEntryStep("welcome");
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [entryStep]);

  // 1.5 Fetch ACS Token as early as possible
  useEffect(() => {
    if (!sessionId || sessionId === "default-session") return;
    fetchRtcToken(sessionId)
      .then(creds => setRtcCreds(creds))
      .catch(err => console.error("ACS token fetch failed", err));
  }, [sessionId]);

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

        // Azure Avatar 실시간 발화 명령 전달
        speakWithCurrentSpeed(message.turn.text);

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
  }, [sessionId, speechSpeed]);

  // 3. Handle transition to 'running' room when waiting and session is running
  useEffect(() => {
    if (entryStep === "waiting" && sessionStatus === "running") {
      setEntryStep("running");
      setOrbState("idle");
    }
  }, [entryStep, sessionStatus]);
  // 4. Log interview history for debugging/future logging purposes
  useEffect(() => {
    if (history.length > 0) {
      console.log("Interview history updated:", history);
    }
  }, [history]);

  const handleAudioChunk = (base64PCM: string) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: "audio.chunk", data: base64PCM }));
    }
  };

  const handleRecordingStart = () => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: "audio.start" }));
    }
  };

  const handleRecordingStop = () => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: "audio.end" }));
    }
  };

  const handleWelcomeStart = async () => {
    setIsExplainerOpen(false);
    setIsChecking(true);
    setErrorMessage("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: true,
      });
      stream.getTracks().forEach((track) => track.stop());
      setEntryStep("consent");
    } catch (err: any) {
      console.error("Permission check failed:", err);
      setErrorMessage("카메라 및 마이크 권한을 허용해 주셔야 인터뷰 진행이 가능합니다.");
    } finally {
      setIsChecking(false);
    }
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
      <div className="app-frame">
        <main className="shell">
          <section className="glass-panel text-center">
            <h1>⚠️ 인터뷰 링크가 필요합니다</h1>
            <p className="muted">담당자가 보내드린 올바른 링크(?session=...)로 접속해 주세요.</p>
          </section>
        </main>
      </div>
    );
  }

  // Step 1: Gromit Screen
  if (entryStep === "gromit") {
    return (
      <div className="app-frame landing-gromit">
        <div className="gromit-text">Gromit</div>
      </div>
    );
  }

  // Step 2: Welcome
  if (entryStep === "welcome") {
    return (
      <div className="app-frame">
        <main className="shell">
          <div className="landing-welcome-container">
            <h1 className="welcome-title">
              {title ? `"${title}"에 온 것을 환영합니다` : "인터뷰에 온 것을 환영합니다"}
            </h1>
            <div className="code-input-panel">
              <button
                className="btn-primary"
                onClick={() => setIsExplainerOpen(true)}
                disabled={isChecking}
              >
                {isChecking ? "권한 확인 중..." : "시작하기"}
              </button>

              <button
                className="btn-secondary"
                onClick={() => {
                  setSessionStatus("running");
                  setEntryStep("running");
                  setStatus("connected");
                }}
                style={{ marginTop: 12, border: "1px solid #3b82f6", color: "#60a5fa" }}
              >
                ⚡ [개발자용] 백룸 없이 아바타 화면 바로 테스트
              </button>

              {errorMessage && <p className="error-alert">{errorMessage}</p>}
            </div>
          </div>

          <PermissionExplainerModal
            isOpen={isExplainerOpen}
            onConfirm={handleWelcomeStart}
          />
        </main>
      </div>
    );
  }

  // Step 4: Pre-Interview Instructions and Consent
  if (entryStep === "consent") {
    return (
      <div className="app-frame">
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
              <button className="btn-secondary" style={{ flex: 1 }} onClick={() => setEntryStep("welcome")}>
                이전
              </button>
              <button className="btn-primary" style={{ flex: 1 }} onClick={handleConsentSubmit} disabled={!isAgreedToRecord || !isAgreedToPrivacy}>
                다음
              </button>
            </div>
          </section>
        </main>
      </div>
    );
  }

  // Step 5: Waiting room
  if (entryStep === "waiting") {
    return (
      <div className="app-frame">
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
          {rtcCreds && (
            <VideoPublisher token={rtcCreds.token} groupId={rtcCreds.group_id} />
          )}
        </main>
      </div>
    );
  }

  // Step 6: Ended or Closed
  if (entryStep === "ended" || sessionStatus === "ended" || status === "closed") {
    return (
      <div className="app-frame">
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
      </div>
    );
  }

  // 4단계: 정상 진행 화면 — 아바타 모니터 / 응답자 모니터 2분할, 스크롤 없는 1화면 프레임
  return (
    <div className="app-frame">
      <main className="stage-shell">
        <header className="main-header stage-header">
          <div className="title-area">
            <span className="live-dot" />
            <h1>{title || "AI 인터뷰"}</h1>
          </div>
        </header>

        <div className="monitor-grid">
          <AvatarMonitor
            videoRef={avatar.videoRef}
            status={avatar.status}
            errorMessage={avatar.errorMessage}
            onRetry={avatar.connect}
            orbState={orbState}
          />
          <RespondentMonitor
            isActive
            isRecording={isRecording}
            onRecordingChange={setIsRecording}
            showMicOffAlert={showMicOffAlert}
            onAudioChunk={handleAudioChunk}
            onRecordingStart={handleRecordingStart}
            onRecordingStop={handleRecordingStop}
          />
          <QuestionPromptBox
            question={question}
            speechSpeed={speechSpeed}
            onSpeedChange={setSpeechSpeed}
            onReplay={() => speakWithCurrentSpeed(question)}
            isSpeaking={avatar.status === "speaking"}
          />
        </div>

        {/* 개발 및 로컬 테스트용 컨트롤 바 */}
        <div style={{ display: "flex", gap: 8, justifyContent: "center", marginTop: 12, alignItems: "center" }}>
          <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
            진행 상황: <strong>{dummyQuestionIndex + 1} / {DUMMY_QUESTIONS.length}</strong>
          </span>
          <button
            className="btn-secondary"
            onClick={() => avatar.speak(question)}
            style={{ fontSize: "0.8rem", padding: "4px 10px" }}
          >
            🔊 현재 질문 다시 말하기
          </button>
          <button
            className="btn-primary"
            onClick={advanceDummyQuestion}
            style={{ fontSize: "0.8rem", padding: "4px 12px", background: "#3b82f6" }}
          >
            ⏭️ 다음 질문으로 넘기기
          </button>
          <button
            className="btn-secondary"
            onClick={() => avatar.connect()}
            style={{ fontSize: "0.8rem", padding: "4px 10px" }}
          >
            🔄 재연결
          </button>
          {(sessionId === "default-session" || isDirectAvatarTest) && (
            <button className="btn-secondary dev-float-btn" onClick={() => setSessionStatus("ended")}>
              [개발자용] 종료 화면
            </button>
          )}
        </div>

        {/* Render headless VideoPublisher if we have the ACS token */}
        {rtcCreds && (
          <VideoPublisher token={rtcCreds.token} groupId={rtcCreds.group_id} />
        )}
      </main>
    </div>
  );
}
