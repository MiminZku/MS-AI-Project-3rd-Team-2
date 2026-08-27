import { useEffect, useRef, useState } from "react";
import { WS_BASE_URL, sessionIdFromUrl } from "./config";
import type { ServerMessage, Turn, QuestionNode } from "./types";
import WaitingScreen from "./components/WaitingScreen";
import InterviewHelpModal from "./components/InterviewHelpModal";
import PermissionExplainerModal from "./components/PermissionExplainerModal";
import { useAudioLevelMonitor } from "./hooks/useAudioLevelMonitor";
import AvatarMonitor from "./components/AvatarMonitor";
import RespondentMonitor from "./components/RespondentMonitor";
import QuestionPromptBox from "./components/QuestionPromptBox";
import VideoPublisher from "./components/VideoPublisher";
import { fetchRtcToken } from "./config";
import { useAvatarWebRTC } from "./hooks/useAvatarWebRTC";
import { useLocalRecording } from "./hooks/useLocalRecording";

type Status = "idle" | "connecting" | "connected" | "closed" | "error";
type SessionStatus = "created" | "running" | "ended";
type EntryStep = "gromit" | "welcome" | "consent" | "waiting" | "running" | "ended";

const INTRO_SELF_REQUEST =
  "본격적인 질문에 앞서, 하시는 일이나 관심 분야 등 간단한 자기소개를 부탁드려도 될까요?";

const DUMMY_QUESTIONS = [
  INTRO_SELF_REQUEST,
  "평소 업무나 일상에서 AI 도구를 얼마나 자주 사용하고 계신가요?",
  "주로 어떤 상황이나 업무에서 AI 도구가 가장 유용하다고 느끼셨나요?",
  "반대로 AI 도구를 사용하시면서 아쉬웠거나 불편했던 점이 있으셨나요?",
  "마지막으로 앞으로 AI 인터뷰나 업무 도구에 바라는 점이 있다면 편하게 말씀해 주세요.",
];

const DUMMY_REACTIONS = [
  "소개 말씀 감사드립니다! 말씀해 주신 내용을 바탕으로 대화를 편안하게 이어가겠습니다. 그럼 첫 번째 질문입니다.",
  "아, 그러셨군요! 자세한 경험 공유 감사드립니다. 그렇다면...",
  "네, 충분히 공감되는 내용이네요. 그렇다면 이번에는...",
  "솔직하고 구체적인 의견 정말 감사드립니다! 많은 도움이 되었습니다. 마지막 질문입니다.",
];

interface OpeningParams {
  projectTitle?: string;
  durationMinutes?: number;
}

function buildOpeningSpeech({ projectTitle, durationMinutes = 15 }: OpeningParams): string {
  const projectGreeting = projectTitle
    ? `"${projectTitle}"에 참여해 주셔서 감사합니다.`
    : "인터뷰에 참여해 주셔서 감사합니다.";
  const durationText = durationMinutes ? `약 ${durationMinutes}분 동안 ` : "";

  return `안녕하세요! ${projectGreeting} 저는 오늘 대화를 진행할 AI 모더레이터입니다. 본 인터뷰는 ${durationText}AI와 나누는 편안한 대화로 진행되며, AI 진행 특성상 대화 호흡이 다소 매끄럽지 못할 수 있는 점 미리 양해 부탁드립니다. 오늘 질문에는 정해진 정답이나 오답이 전혀 없으니, 평소 느끼고 경험하신 생각을 편안하고 솔직하게 말씀해 주시면 됩니다. 본격적인 질문에 앞서, 하시는 일이나 관심 분야 등 간단한 자기소개를 부탁드려도 될까요?`;
}

const INTERPRETATION_LANGUAGE_LABELS: Record<string, string> = {
  ko: "한국어",
  en: "English",
  ja: "日本語",
};

export default function App() {
  const [sessionId] = useState(sessionIdFromUrl);
  const [, setStatus] = useState<Status>("idle");
  // URL 파라미터에 test=avatar 가 있거나 빠른 테스트 지원
  const isDirectAvatarTest = new URLSearchParams(window.location.search).get("test") === "avatar";
  const [entryStep, setEntryStep] = useState<EntryStep>(isDirectAvatarTest ? "running" : "gromit");
  const [sessionStatus, setSessionStatus] = useState<SessionStatus>(isDirectAvatarTest ? "running" : "created");
  const [rtcCreds, setRtcCreds] = useState<{ token: string; group_id: string } | null>(null);

  // Flow states
  const [isRecording, setIsRecording] = useState(false);
  const [isChecking, setIsChecking] = useState(false);
  const [isExplainerOpen, setIsExplainerOpen] = useState(false);
  const [isHelpOpen, setIsHelpOpen] = useState(false);
  const [isAgreedToRecord, setIsAgreedToRecord] = useState(false);
  const [isAgreedToPrivacy, setIsAgreedToPrivacy] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const [projectTitle, setProjectTitle] = useState(isDirectAvatarTest ? "AI 도구 사용 경험 인터뷰" : "");
  const [durationMinutes, setDurationMinutes] = useState<number>(15);
  const [interpretationLanguage, setInterpretationLanguage] = useState<string>("");
  const [sessionQuestions, setSessionQuestions] = useState<QuestionNode[]>([]);
  const [dummyQuestionIndex, setDummyQuestionIndex] = useState(0);
  const [question, setQuestion] = useState(DUMMY_QUESTIONS[0]);
  const [speechSpeed, setSpeechSpeed] = useState<number>(1.1); // 기본 1.1x — 1.25x는 발음이 뭉개진다는 QC 피드백 반영, 사용자가 화면에서 직접 올릴 수 있음
  const [history, setHistory] = useState<Turn[]>([]);
  const [isWaitingForAdditional, setIsWaitingForAdditional] = useState(false);
  // 세션이 종료됐지만 아바타의 작별 인사가 아직 재생 중인 상태
  const [isPendingEnd, setIsPendingEnd] = useState(false);

  // Constant audio level monitor when on running step
  const isVoiceDetected = useAudioLevelMonitor(entryStep === "running");
  const showMicOffAlert = isVoiceDetected && !isRecording;

  const [orbState, setOrbState] = useState<"idle" | "speaking" | "listening">("idle");
  const socketRef = useRef<WebSocket | null>(null);
  const hasSpokenIntroRef = useRef(false);
  const wrapUpTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hasSpokenEndRef = useRef(false);
  const hasActuallySpokenRef = useRef(false);

  // 마이크가 켜져 있는 동안 실제 사람 목소리가 감지되었는지 실시간 추적
  useEffect(() => {
    if (isRecording && isVoiceDetected) {
      hasActuallySpokenRef.current = true;
    }
  }, [isRecording, isVoiceDetected]);

  const { isRecording: isLocalRecording, startRecording, stopAndUploadRecording } = useLocalRecording();
  const mediaStreamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    if (entryStep === "running" && !isLocalRecording) {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ video: true, audio: true })
          .then(stream => {
            mediaStreamRef.current = stream;
            startRecording(stream);
          })
          .catch(err => console.error("로컬 녹화 스트림 확보 실패:", err));
      } else {
        console.error("이 브라우저 환경(HTTP 등)에서는 카메라/마이크 접근이 제한되어 로컬 녹화를 시작할 수 없습니다.");
      }
    }
  }, [entryStep, isLocalRecording, startRecording]);

  useEffect(() => {
    // 세션이 완전히 끝나면 녹화를 멈추고 서버로 업로드
    if (entryStep === "ended") {
      stopAndUploadRecording(sessionId).catch(err => console.error("업로드 에러:", err));
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach(track => track.stop());
      }
    }
  }, [entryStep, sessionId, stopAndUploadRecording]);

  // Azure Avatar WebRTC 훅 연동 (Lisa 아바타 & 다국어 음성)
  const avatar = useAvatarWebRTC({
    autoConnect: entryStep === "running",
    character: "lisa",
    style: "casual-sitting",
    voice: "en-US-AvaMultilingualNeural",
  });

  const speakWithCurrentSpeed = (text: string) => {
    avatar.speak(text, undefined, speechSpeed);
  };

  // 0. 메인룸 입장 시 아바타가 먼저 인사 및 AI 인터뷰 공지 발화 (동적 오프닝 멘트 자동 발화)
  useEffect(() => {
    if (entryStep === "running" && avatar.status === "connected" && !hasSpokenIntroRef.current) {
      hasSpokenIntroRef.current = true;
      setOrbState("speaking");

      // 0.8초 후 오프닝 멘트를 백엔드에 전달 (백엔드에서 assistant.question으로 내려주어 발화)
      const timer = setTimeout(() => {
        const fullIntroSpeech = buildOpeningSpeech({
          projectTitle,
          durationMinutes,
        });

        if (socketRef.current?.readyState === WebSocket.OPEN) {
          // 백엔드로 전송하면 백엔드에서 'assistant.question' 이벤트를 통해 똑같은 멘트를 내려줍니다.
          // 프론트는 그걸 받아서 발화하므로, 여기서 직접 발화(speak)하면 이중 발화가 됩니다.
          socketRef.current.send(
            JSON.stringify({ type: "intro.spoken", text: fullIntroSpeech }),
          );
        } else {
          // 오프라인(더미) 모드일 때만 직접 발화
          setQuestion(fullIntroSpeech);
          speakWithCurrentSpeed(fullIntroSpeech);
          setTimeout(() => {
            setOrbState("listening");
          }, 12000);
        }
      }, 800);

      return () => clearTimeout(timer);
    }
  }, [entryStep, avatar.status, projectTitle, durationMinutes, speechSpeed]);

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
        setProjectTitle(message.session.project_title?.trim() || message.session.title?.trim() || "");
        if (message.session.status === "ended") {
          // 백엔드는 AI 작별 인사를 보낸 직후 세션을 자동 종료한다. 여기서 곧바로 종료 화면으로
          // 갈아치우면 아바타가 인사를 말하는 도중에 잘리므로, 발화가 끝난 뒤에 전환한다.
          setIsPendingEnd(true);
        } else {
          setSessionStatus(message.session.status);
        }
        if (message.session.duration_minutes) {
          setDurationMinutes(message.session.duration_minutes);
        }
        if (message.session.interpretation_language) {
          setInterpretationLanguage(message.session.interpretation_language);
        }
        if (message.session.questions && message.session.questions.length > 0) {
          setSessionQuestions(message.session.questions);
        }
      } else if (message.type === "assistant.question") {
        // 실제 백엔드 LLM이 생성한 다음 질문 수신 -> 아바타 음성 및 자막 실시간 발화!
        const questionText = message.turn.text;
        if (wrapUpTimerRef.current) {
          clearTimeout(wrapUpTimerRef.current);
          wrapUpTimerRef.current = null;
        }

        // 이미 종료 멘트를 발화한 상태라면 중복 발화 차단
        if (questionText.includes("인터뷰를 모두 마치겠습니다") && hasSpokenEndRef.current) {
          return;
        }
        if (questionText.includes("인터뷰를 모두 마치겠습니다")) {
          hasSpokenEndRef.current = true;
        }

        setQuestion(questionText);
        setHistory((prev) => [...prev, message.turn]);
        setOrbState("speaking");

        speakWithCurrentSpeed(questionText);

        // 랩업 또는 종료 상태 감지
        if (questionText.includes("리서치팀에서 추가로 확인") || questionText.includes("잠시 확인해 보겠습니다")) {
          setIsWaitingForAdditional(true);
        } else if (questionText.includes("인터뷰를 모두 마치겠습니다") || questionText.includes("종료되었습니다")) {
          setIsWaitingForAdditional(false);
        }

        // 아바타 발화 시간 후 리스닝 상태로 전환 (응답자 마이크 준비)
        setTimeout(() => {
          if (!questionText.includes("인터뷰를 모두 마치겠습니다")) {
            setOrbState("listening");
          } else {
            setOrbState("idle");
          }
        }, 4500);
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

  // 3-1. 자동 종료 신호를 받았어도 아바타가 말하는 중이면 기다렸다가 종료 화면으로 전환한다.
  // avatar.status 는 발화가 끝나면 "connected" 로 돌아오므로 그때 전환한다.
  // (아바타가 아예 발화를 시작하지 못한 경우를 대비해 짧은 유예 시간을 둔다.)
  useEffect(() => {
    if (!isPendingEnd || avatar.status === "speaking") return;
    const timer = setTimeout(() => setSessionStatus("ended"), 1200);
    return () => clearTimeout(timer);
  }, [isPendingEnd, avatar.status]);
  // 3-2. 위 전환은 avatar.status가 "speaking"에서 벗어나야 발동하는데, 아바타 음성 합성이
  // 네트워크 문제 등으로 응답을 영영 안 주면 status가 "speaking"에 멈춰서 종료 화면이 영원히
  // 안 뜬다 — PM이 대시보드에서 종료를 눌러도 인터뷰이 화면이 계속 살아있는 것처럼 보이는
  // 원인. avatar.status와 무관하게 최대 대기 시간을 두어 반드시 종료 화면으로 넘어가게 한다.
  useEffect(() => {
    if (!isPendingEnd) return;
    const timer = setTimeout(() => setSessionStatus("ended"), 8000);
    return () => clearTimeout(timer);
  }, [isPendingEnd]);
  // 4. Log interview history for debugging/future logging purposes
  useEffect(() => {
    if (history.length > 0) {
      console.log("Interview history updated:", history);
    }
  }, [history]);

  // 더미 질문 순차 진행 함수 (핑퐁 제어 및 맞장구 리액션)
  // 백룸 추가 질문 주입 시뮬레이션 (개발/테스트용)
  const injectObserverFollowUpQuestion = () => {
    const injectedQuestion =
      "리서치팀에서 추가 확인 요청이 들어왔습니다. 혹시 가장 기억에 남는 AI 도구 사용 경험이나 계기가 있으시다면 한 가지만 더 들려주실 수 있을까요?";
    setQuestion(injectedQuestion);
    setOrbState("speaking");
    speakWithCurrentSpeed(injectedQuestion);
    setIsWaitingForAdditional(false);
  };

  // 더미/폴백 질문 순차 진행 함수 (핑퐁 제어 및 마지막 백룸 개입 확인 랩업)
  const advanceDummyQuestion = () => {
    const questionsList = sessionQuestions.length > 0
      ? [INTRO_SELF_REQUEST, ...sessionQuestions.map(q => q.text)]
      : DUMMY_QUESTIONS;

    const nextIdx = dummyQuestionIndex + 1;
    if (nextIdx < questionsList.length) {
      setDummyQuestionIndex(nextIdx);
      const rawQuestion = questionsList[nextIdx];
      const reactionPrefix = DUMMY_REACTIONS[nextIdx - 1] || "네, 말씀 감사합니다. 다음 질문입니다.";
      
      // 아바타 음성은 "맞장구 + 다음 질문"으로 자연스럽게 발화
      const fullSpeech = `${reactionPrefix} ${rawQuestion}`;
      // 하단 텍스트 박스에 발화하는 전체 문장 표시 (음성과 자막 완벽 일치)
      setQuestion(fullSpeech);
      setOrbState("speaking");
      speakWithCurrentSpeed(fullSpeech);
    } else {
      // 모든 기본 질문 완료 -> 백룸(리서치팀) 추가 질문 여부 확인 단계로 진입
      setIsWaitingForAdditional(true);
      const wrapUpCheckSpeech =
        "준비된 기본 질문은 모두 마쳤습니다! 혹시 참관 중인 리서치팀에서 추가로 확인하고 싶은 내용이 있는지 잠시 확인해 보겠습니다. 잠시만 기다려 주세요.";
      setQuestion(wrapUpCheckSpeech);
      setOrbState("speaking");
      speakWithCurrentSpeed(wrapUpCheckSpeech);

      // 백엔드 소켓이 없을 때만(오프라인 더미 모드) 7.5초 후 1회 안전 종료
      if (socketRef.current?.readyState !== WebSocket.OPEN) {
        if (wrapUpTimerRef.current) clearTimeout(wrapUpTimerRef.current);
        wrapUpTimerRef.current = setTimeout(() => {
          setIsWaitingForAdditional((currentWaiting) => {
            if (currentWaiting && !hasSpokenEndRef.current) {
              hasSpokenEndRef.current = true;
              const finalEndSpeech =
                "확인 결과 추가 질문은 없으므로 오늘 인터뷰를 모두 마치겠습니다. 성실하고 소중한 답변 진심으로 감사드립니다! 상단의 나가기 버튼을 눌러 퇴장해 주시면 됩니다.";
              setQuestion(finalEndSpeech);
              setOrbState("speaking");
              speakWithCurrentSpeed(finalEndSpeech);
              return false;
            }
            return false;
          });
        }, 7500);
      }
    }
  };

  const handleAudioChunk = (base64PCM: string) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: "audio.chunk", data: base64PCM }));
    }
  };

  const recordingStartTimeRef = useRef<number>(0);

  const handleRecordingStart = () => {
    // 1. 마이크 켜질 때 실제 발화 감지 플래그 초기화
    hasActuallySpokenRef.current = false;
    recordingStartTimeRef.current = Date.now();
    setOrbState("listening");

    // 2. 아바타 발화는 중단하되, 현재 자막 텍스트는 절대 날아가지 않고 그대로 유지!
    avatar.stopSpeaking();

    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: "audio.start" }));
    }
  };

  const handleRecordingStop = () => {
    const duration = Date.now() - recordingStartTimeRef.current;
    const hasSpoken = hasActuallySpokenRef.current || duration >= 1500;

    // 실제 음성이 전혀 감지되지 않았고 1.5초 미만으로 마이크만 껐다면 -> 턴을 넘기지 않고 현재 질문 유지!
    if (!hasSpoken) {
      console.log("실제 음성이 감지되지 않았습니다. 현재 질문 자막을 그대로 유지합니다.");
      setOrbState("listening");
      return;
    }

    // 1. 백엔드 WebSocket이 연결되어 있는 경우 -> 백엔드에 발화 종료 알림 (STT & LLM 다음 질문 생성 트리거)
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      setOrbState("speaking");
      socketRef.current.send(JSON.stringify({ type: "audio.end" }));
      return;
    }

    // 2. 소켓 연결이 없는 로컬 단독 테스트 모드: 실제 답변이 감지된 경우에만 다음 질문으로 핑퐁 진행!
    console.log("Mock: 실제 답변 발화 감지됨 -> 다음 대본 질문으로 이동");
    setOrbState("speaking");
    setTimeout(() => {
      advanceDummyQuestion();
    }, 800);
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
              {projectTitle ? `"${projectTitle}"에 참여해 주셔서 감사합니다.` : "인터뷰에 참여해 주셔서 감사합니다."}
            </h1>
            <div className="code-input-panel">
              <button
                className="btn-primary"
                onClick={() => setIsExplainerOpen(true)}
                disabled={isChecking}
              >
                {isChecking ? "권한 확인 중..." : "시작하기"}
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
          <WaitingScreen title={projectTitle} onOpenHelp={() => setIsHelpOpen(true)} />
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
          <InterviewHelpModal isOpen={isHelpOpen} onClose={() => setIsHelpOpen(false)} />
        </main>
      </div>
    );
  }

  // Step 6: Ended (사용자가 직접 나가기를 누르거나 명시적으로 ended 되었을 때만)
  if (entryStep === "ended" || sessionStatus === "ended") {
    return (
      <div className="app-frame">
        <main className="shell">
          <section className="glass-panel text-center">
            <h2>🎉 인터뷰가 종료되었습니다</h2>
            <p className="muted" style={{ lineHeight: 1.6, marginTop: 12 }}>
              성실하게 답변에 임해 주셔서 대단히 감사합니다.<br />
              이제 브라우저 창을 닫으셔도 좋습니다.
            </p>
          </section>
          {(sessionId === "default-session" || isDirectAvatarTest) && (
            <div style={{ textAlign: "center", marginTop: 20 }}>
              <button className="btn-secondary" onClick={() => { setSessionStatus("running"); setEntryStep("running"); setStatus("connected"); }}>
                [개발자용] 다시 진행 화면으로 복귀
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
        <header className="main-header stage-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div className="title-area" style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <h1>{projectTitle || "AI 인터뷰"}</h1>
          </div>
          <div style={{ fontSize: "0.8rem", color: "var(--muted)", display: "flex", alignItems: "center", gap: 8 }}>
            <span>예정 시간: 약 {durationMinutes}분</span>
          </div>
          <button
            className="interview-help-trigger"
            type="button"
            aria-label="인터뷰 이용 안내 열기"
            onClick={() => setIsHelpOpen(true)}
          >
            ?
          </button>
        </header>

        <div className="monitor-grid">
          <AvatarMonitor
            videoRef={avatar.videoRef}
            status={avatar.status}
            errorMessage={avatar.errorMessage}
            onRetry={avatar.connect}
            orbState={orbState}
            speechSpeed={speechSpeed}
            onSpeedChange={setSpeechSpeed}
          />
          <RespondentMonitor
            isActive
            isRecording={isRecording}
            onRecordingChange={setIsRecording}
            showMicOffAlert={showMicOffAlert}
            onAudioChunk={handleAudioChunk}
            onRecordingStart={handleRecordingStart}
            onRecordingStop={handleRecordingStop}
            onEndInterview={() => {
              if (window.confirm("인터뷰를 종료하고 퇴장하시겠습니까?")) {
                setEntryStep("ended");
                setSessionStatus("ended");
              }
            }}
          />
          <QuestionPromptBox
            question={question}
            onReplay={() => speakWithCurrentSpeed(question)}
            isSpeaking={avatar.status === "speaking"}
          />
          {interpretationLanguage && (
            <div
              style={{
                marginTop: 6,
                textAlign: "right",
                fontSize: "0.72rem",
                color: "rgba(148, 163, 184, 0.9)",
              }}
            >
              동시통역: {INTERPRETATION_LANGUAGE_LABELS[interpretationLanguage] ?? interpretationLanguage}
            </div>
          )}
        </div>

        {/* 백룸(리서치팀) 추가 질문 대기 상태 배너 & 개발 테스트 버튼 */}
        {isWaitingForAdditional && (
          <div
            style={{
              marginTop: 10,
              padding: "8px 16px",
              background: "rgba(59, 130, 246, 0.15)",
              border: "1px solid rgba(59, 130, 246, 0.3)",
              borderRadius: "10px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 12,
              backdropFilter: "blur(8px)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.82rem", color: "#93c5fd" }}>
              <span className="live-dot" style={{ background: "#3b82f6" }} />
              <span>🔍 리서치팀(백룸)의 추가 질문 여부를 확인하고 있습니다...</span>
            </div>

            {(sessionId === "default-session" || isDirectAvatarTest) && (
              <button
                onClick={injectObserverFollowUpQuestion}
                style={{
                  background: "#2563eb",
                  color: "white",
                  border: "none",
                  padding: "4px 10px",
                  borderRadius: "6px",
                  fontSize: "0.75rem",
                  cursor: "pointer",
                  fontWeight: 500,
                  whiteSpace: "nowrap",
                }}
              >
                ⚡ [테스트] 백룸 추가 질문 주입 시뮬레이션
              </button>
            )}
          </div>
        )}

        {/* Render headless VideoPublisher if we have the ACS token */}
        {rtcCreds && (
          <VideoPublisher token={rtcCreds.token} groupId={rtcCreds.group_id} />
        )}
        <InterviewHelpModal isOpen={isHelpOpen} onClose={() => setIsHelpOpen(false)} />
      </main>
    </div>
  );
}
