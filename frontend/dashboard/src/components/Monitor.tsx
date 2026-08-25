import { useCallback, useEffect, useRef, useState } from "react";
import type { Role } from "../App";
import { startSession, endSession, fetchReport, observerSocketUrl, fetchRtcToken, getProject, uploadGuideFile } from "../api";
import { DEMO_INSTRUCTIONS, DEMO_REPORT, DEMO_SESSION, DEMO_SESSION_ID, DEMO_TRANSCRIPT } from "../demoData";
import { useRemoteRecording } from "../hooks/useRemoteRecording";
import VideoSubscriber from "./VideoSubscriber";
import type { Instruction, Report, ServerMessage, Session, Turn } from "../types";

interface Props {
  sessionId: string;
  intervieweeUrl: string;
  role: Role;
  onStatusChange?: (status: TopbarStatus | null) => void;
}

interface Timekeeper {
  should_move_on: boolean;
  remaining_minutes: number;
  remaining_questions: number;
  hint: string;
}

export type Phase = "wait" | "joined" | "live" | "end";

/** App.tsx 상단바가 렌더링할 세션 제어 상태 — Monitor가 웹소켓/세션 상태를 들고 있어서 콜백으로 끌어올린다. */
export interface TopbarStatus {
  role: Role;
  phase: Phase;
  starting: boolean;
  ending: boolean;
  hasReport: boolean;
  onStartSession: () => void;
  onEndSession: () => void;
  onOpenReport: () => void;
}

const FILE_FORMATS = [
  { key: "md", label: "Markdown", accept: ".md,text/markdown" },
  {
    key: "word",
    label: "Word",
    accept: ".doc,.docx,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  },
  { key: "pdf", label: "PDF", accept: ".pdf,application/pdf" },
] as const;

type FileFormat = (typeof FILE_FORMATS)[number]["key"];

const QUICK_INSTRUCTIONS = [
  "방금 답변을 더 구체적으로 캐물어봐 주세요.",
  "경쟁 앱과 비교해서 물어봐 주세요.",
  "다음 주제로 자연스럽게 넘어가 주세요.",
];

const LANGUAGE_LABELS: Record<string, string> = { ko: "한국어", en: "English", ja: "日本語" };

function phaseOf(session: Session | null, intervieweeOnline: boolean): Phase {
  if (!session || session.status === "created") {
    return intervieweeOnline ? "joined" : "wait";
  }
  return session.status === "running" ? "live" : "end";
}

function formatMMSS(totalSeconds: number): string {
  const clamped = Math.max(0, Math.floor(totalSeconds));
  const mm = String(Math.floor(clamped / 60)).padStart(2, "0");
  const ss = String(clamped % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

export default function Monitor({ sessionId, intervieweeUrl, role, onStatusChange }: Props) {
  const [session, setSession] = useState<Session | null>(null);
  const [transcript, setTranscript] = useState<Turn[]>([]);
  const [instructions, setInstructions] = useState<Instruction[]>([]);
  const [timekeeper, setTimekeeper] = useState<Timekeeper | null>(null);
  const [intervieweeOnline, setIntervieweeOnline] = useState(false);
  const [status, setStatus] = useState("connecting");
  const [draft, setDraft] = useState("");
  const [liveTextKo, setLiveTextKo] = useState("");
  const [liveTextEn, setLiveTextEn] = useState("");
  const liveTextEnRef = useRef("");
  const pendingTranslationIndexRef = useRef<number | null>(null);
  const [showTranslation, setShowTranslation] = useState(false);
  const [translations, setTranslations] = useState<Record<number, string>>({});
  const [report, setReport] = useState<Report | null>(null);
  const [starting, setStarting] = useState(false);
  const [ending, setEnding] = useState(false);
  const [recordingRequested, setRecordingRequested] = useState(false);
  const [remoteStream, setRemoteStream] = useState<MediaStream | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [rtcCreds, setRtcCreds] = useState<{ token: string; group_id: string } | null>(null);
  // 백엔드가 세션 상태를 자동으로 넘겨주기 전까지, 화면 미리보기용 수동 오버라이드.
  const [historyOpen, setHistoryOpen] = useState(false);
  const [instructionsOpen, setInstructionsOpen] = useState(false);
  const [activePanel, setActivePanel] = useState<"tree" | "link" | "options" | null>(null);
  const [clientAccessId, setClientAccessId] = useState<string | null>(null);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [fileFormat, setFileFormat] = useState<FileFormat>("md");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadingGuide, setUploadingGuide] = useState(false);
  const [drawerPinned, setDrawerPinned] = useState(false);
  const { startRecording, stopAndUploadRecording } = useRemoteRecording();
  const socketRef = useRef<WebSocket | null>(null);
  const drawerRef = useRef<HTMLDivElement | null>(null);
  const reportRef = useRef<HTMLDivElement | null>(null);
  const dockRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!activePanel) return;
    const handleOutsideClick = (event: MouseEvent) => {
      if (dockRef.current && !dockRef.current.contains(event.target as Node)) {
        setActivePanel(null);
      }
    };
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, [activePanel]);

  useEffect(() => {
    if (sessionId !== DEMO_SESSION_ID) {
      fetchRtcToken(sessionId)
        .then(creds => setRtcCreds(creds))
        .catch(err => console.error("ACS token fetch failed", err));
    }
  }, [sessionId]);

  useEffect(() => {
    if (!session?.study_id || sessionId === DEMO_SESSION_ID) return;
    getProject(session.study_id)
      .then((project) => setClientAccessId(project.access_id ?? null))
      .catch((err) => console.error("프로젝트 조회 실패", err));
  }, [session?.study_id, sessionId]);

  useEffect(() => {
    // 백엔드 없이 화면을 리뷰하기 위한 목데이터 모드 (§SessionForm "데모로 미리보기").
    if (sessionId === DEMO_SESSION_ID) {
      setSession(DEMO_SESSION);
      setTranscript(DEMO_TRANSCRIPT);
      setInstructions(DEMO_INSTRUCTIONS);
      setIntervieweeOnline(true);
      setStatus("connected");
      return;
    }

    const socket = new WebSocket(observerSocketUrl(sessionId));
    socketRef.current = socket;

    socket.onopen = () => setStatus("connected");
    socket.onclose = () => setStatus("closed");
    socket.onerror = () => setStatus("error");
    socket.onmessage = (event) => {
      const message: ServerMessage = JSON.parse(event.data);
      switch (message.type) {
        case "session.state":
          setSession((prev) => (prev ? { ...prev, ...message.session } : (message.session as Session)));
          break;
        case "session.snapshot":
          setSession(message.session);
          setTranscript(message.transcript);
          setInstructions(message.instructions);
          setIntervieweeOnline(message.interviewee_connected);
          break;
        case "transcript.append":
          setTranscript((prev) => [...prev, message.turn]);
          if (message.turn.speaker === "interviewee") {
            const idx = message.turn.index;
            if (message.turn.text_en) {
              setTranslations((prev) => ({ ...prev, [idx]: message.turn.text_en! }));
              pendingTranslationIndexRef.current = null;
            } else if (liveTextEnRef.current) {
              const text = liveTextEnRef.current;
              setTranslations((prev) => ({ ...prev, [idx]: text }));
              pendingTranslationIndexRef.current = idx;
            } else {
              pendingTranslationIndexRef.current = idx;
            }
            liveTextEnRef.current = "";
          } else {
            pendingTranslationIndexRef.current = null;
            liveTextEnRef.current = "";
          }
          break;
        case "transcript.partial":
        case "transcript.final":
          if (message.lang === "ko") setLiveTextKo(message.text);
          if (message.lang === "en") {
            setLiveTextEn(message.text);
            liveTextEnRef.current = message.text;
            if (pendingTranslationIndexRef.current !== null) {
              const idx = pendingTranslationIndexRef.current;
              const text = message.text;
              setTranslations((prev) => ({ ...prev, [idx]: text }));
              if (message.type === "transcript.final") pendingTranslationIndexRef.current = null;
            }
          }
          break;
        case "instruction.queued":
          setInstructions((prev) => [...prev, message.instruction]);
          break;
        case "instruction.applied":
          // queued -> applied 전환 (§4.1-7)
          setInstructions((prev) =>
            prev.map((item) =>
              item.id === message.instruction.id ? message.instruction : item,
            ),
          );
          break;
        case "timekeeper.signal":
          setTimekeeper(message);
          break;
        case "session.started":
          setSession(message.session);
          break;
        case "session.ended":
          setSession(message.session);
          break;
        case "report.ready":
          setReport(message.report);
          break;
        case "interviewee.connected":
          setIntervieweeOnline(true);
          break;
        case "interviewee.disconnected":
          setIntervieweeOnline(false);
          break;
      }
    };

    return () => socket.close();
  }, [sessionId]);

  // report.ready 이벤트를 놓쳤을 경우를 대비한 폴백 폴링.
  useEffect(() => {
    if (sessionId === DEMO_SESSION_ID || session?.status !== "ended" || report) return;
    let cancelled = false;
    const poll = async () => {
      const result = await fetchReport(sessionId).catch(() => null);
      if (!cancelled && result) setReport(result);
    };
    poll();
    const timer = setInterval(poll, 4000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [sessionId, session?.status, report]);

  useEffect(() => {
    if (session?.status !== "running" || !session.started_at) return;
    const startedAt = new Date(session.started_at).getTime();
    const tick = () => setElapsedSec((Date.now() - startedAt) / 1000);
    tick();
    const timer = setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, [session?.status, session?.started_at]);

  useEffect(() => {
    if (!recordingRequested || session?.status !== "running" || !remoteStream) return;
    startRecording(remoteStream);
  }, [recordingRequested, remoteStream, session?.status, startRecording]);

  useEffect(() => {
    if (!drawerPinned) return;
    const closeOnOutsidePointer = (event: PointerEvent) => {
      if (!drawerRef.current?.contains(event.target as Node)) setDrawerPinned(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setDrawerPinned(false);
    };
    document.addEventListener("pointerdown", closeOnOutsidePointer);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsidePointer);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [drawerPinned]);

  const sendInstruction = () => {
    const text = draft.trim();
    const socket = socketRef.current;
    if (!text || socket?.readyState !== WebSocket.OPEN) return;
    socket.send(JSON.stringify({ type: "instruction.create", text }));
    setDraft("");
  };

  const handleStartSession = useCallback(async () => {
    setStarting(true);
    if (sessionId === DEMO_SESSION_ID) {
      const startedAt = new Date().toISOString();
      setSession((prev) => (prev ? { ...prev, status: "running", started_at: startedAt } : prev));
    } else {
      await startSession(sessionId).catch((err) => console.error("세션 시작 실패:", err));
      setSession((prev) => (prev ? { ...prev, status: "running", started_at: new Date().toISOString() } : prev));
    }
    setStarting(false);
  }, [sessionId]);

  const handleEndSession = useCallback(async () => {
    setEnding(true);
    setRecordingRequested(false);
    setActionError(null);
    if (sessionId === DEMO_SESSION_ID) {
      const endedAt = new Date().toISOString();
      setSession((prev) => (prev ? { ...prev, status: "ended", ended_at: endedAt } : prev));
      setTimeout(() => setReport(DEMO_REPORT), 1500);
    } else {
      try {
        await stopAndUploadRecording(sessionId);
      } catch (error) {
        console.error("Failed to upload interview recording", error);
        setActionError("녹화 파일 업로드에 실패했습니다. 인터뷰는 종료합니다.");
      }
      try {
        setSession(await endSession(sessionId));
      } catch (error) {
        console.error("Failed to end interview", error);
        setActionError("인터뷰를 종료하지 못했습니다. 다시 시도해 주세요.");
      }
    }
    setEnding(false);
  }, [sessionId, stopAndUploadRecording]);

  const handleOpenReport = useCallback(() => {
    reportRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const phase = phaseOf(session, intervieweeOnline);
  const questions = session?.questions ?? [];

  const finalElapsedSec =
    session?.started_at && session?.ended_at
      ? (new Date(session.ended_at).getTime() - new Date(session.started_at).getTime()) / 1000
      : 0;
  const timerLabel =
    phase === "live"
      ? formatMMSS(elapsedSec)
      : phase === "end"
        ? formatMMSS(finalElapsedSec)
        : "00:00";
  const phaseLabel = { wait: "대기", joined: "입장함", live: "경과", end: "종료" }[phase];
  const statusLabel: Record<Phase, string> = { wait: "대기", joined: "입장함", live: "진행 중", end: "종료" };

  useEffect(() => {
    onStatusChange?.({
      role,
      phase,
      starting,
      ending,
      hasReport: report != null,
      onStartSession: handleStartSession,
      onEndSession: handleEndSession,
      onOpenReport: handleOpenReport,
    });
  }, [role, phase, starting, ending, report, handleStartSession, handleEndSession, handleOpenReport, onStatusChange]);

  // Monitor가 언마운트될 때만(세션 목록으로 돌아갈 때) 상단바 상태를 지운다.
  useEffect(() => () => onStatusChange?.(null), [onStatusChange]);

  return (
    <>
      <div className="tabbar">
        <div ref={dockRef} className="dock-shell">
        <div className="dock-edge-trigger" />
        <div className="dock-wrap">
        <div className="dock">
          <button
            type="button"
            className={`dock-icon tree ${activePanel === "tree" ? "on" : ""}`}
            title="질문 트리 · 질문 등록/편집"
            onClick={() => setActivePanel((v) => (v === "tree" ? null : "tree"))}
          >
            <span className="dock-icon-glyph">
              <svg width="21" height="21" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="10" cy="3.6" r="1.6" fill="currentColor" stroke="none" />
                <path d="M10 5.2V9" />
                <path d="M5 15V9h10v6" />
                <circle cx="5" cy="16.4" r="1.6" fill="currentColor" stroke="none" />
                <circle cx="15" cy="16.4" r="1.6" fill="currentColor" stroke="none" />
              </svg>
            </span>
          </button>
          <button
            type="button"
            className={`dock-icon link ${activePanel === "link" ? "on" : ""}`}
            title="세션 링크"
            onClick={() => setActivePanel((v) => (v === "link" ? null : "link"))}
          >
            <span className="dock-icon-glyph">
              <svg width="21" height="21" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                <path d="M7.5 13.5a3 3 0 0 1 0-4.24l2-2a3 3 0 0 1 4.24 4.24l-1 1" />
                <path d="M12.5 6.5a3 3 0 0 1 0 4.24l-2 2a3 3 0 0 1-4.24-4.24l1-1" />
              </svg>
            </span>
          </button>
          <button type="button" className="dock-icon analysis" disabled title="분석 앱 연동 전 · URL 확정 후 연결">
            <span className="dock-icon-glyph">
              <svg width="21" height="21" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 16V11" />
                <path d="M10 16V6" />
                <path d="M16 16V13" />
              </svg>
            </span>
          </button>
          <button
            type="button"
            className={`dock-icon options ${activePanel === "options" ? "on" : ""}`}
            title="세션 옵션 · 인터뷰 시간 · 통역 언어"
            onClick={() => setActivePanel((v) => (v === "options" ? null : "options"))}
          >
            <span className="dock-icon-glyph">
              <svg width="21" height="21" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="10" cy="10" r="2.2" />
                <path d="M10 3.5v2M10 14.5v2M16.5 10h-2M5.5 10h-2M14.6 5.4l-1.4 1.4M6.8 13.2l-1.4 1.4M14.6 14.6l-1.4-1.4M6.8 6.8L5.4 5.4" />
              </svg>
            </span>
          </button>
        </div>
        </div>

          <div className={`dock-panel ${activePanel === "tree" ? "open" : ""}`}>
            <div className="hover-drawer-section">
              <div className="hover-drawer-label">• 질문 트리</div>
              <div className="accordion-actions">
                {role === "pm" ? (
                  <button type="button" className="btn-sm solid" onClick={() => setEditModalOpen(true)}>
                    ＋ 질문 등록 및 편집
                  </button>
                ) : (
                  <span className="role-chip" style={{ fontSize: "10px" }}>
                    참관 전용
                  </span>
                )}
              </div>
              <ol className="tree">
                {questions.map((question, index) => {
                  const current = index === session?.current_question_index;
                  const done = session != null && index < session.current_question_index;
                  return (
                    <li key={question.id} className={current ? "current" : done ? "done" : ""}>
                      <span className="q-num">{index + 1}</span>
                      <div className="q-body">
                        {question.text}
                        {Object.entries(question.branches).map(([condition, followUp]) => {
                          const isBranchActive =
                            current &&
                            session?.active_branch != null &&
                            (session.active_branch.includes(condition) ||
                              condition.includes(session.active_branch) ||
                              session.active_branch.includes(followUp) ||
                              followUp.includes(session.active_branch));

                          const isBranchTaken =
                            session?.taken_branches?.some(
                              (tb) =>
                                tb.includes(condition) ||
                                condition.includes(tb) ||
                                tb.includes(followUp) ||
                                followUp.includes(tb)
                            ) ?? false;

                          return (
                            <div
                              key={condition}
                              className={`branch ${
                                isBranchActive ? "active" : isBranchTaken ? "taken" : ""
                              }`}
                            >
                              <div className="branch-header">
                                <span className="cond">{condition}</span>
                                {isBranchActive && (
                                  <span className="branch-badge live">진행 중</span>
                                )}
                                {isBranchTaken && !isBranchActive && (
                                  <span className="branch-badge done">완료</span>
                                )}
                              </div>
                              <span className="branch-q">{followUp}</span>
                            </div>
                          );
                        })}
                      </div>
                    </li>
                  );
                })}
              </ol>

              {timekeeper && (
                <div className={`timekeeper ${timekeeper.should_move_on ? "warn" : ""}`} style={{ margin: "0 16px 16px" }}>
                  <strong>타임키퍼</strong>
                  <p>{timekeeper.hint}</p>
                </div>
              )}
            </div>
          </div>

          <div className={`dock-panel ${activePanel === "link" ? "open" : ""}`}>
            <div className="hover-drawer-section">
              <div className="hover-drawer-label">• 세션 링크</div>
              <div className="p-body">
                {role === "pm" ? (
                  <>
                    {intervieweeUrl && (
                      <p className="link-row">
                        인터뷰이: <code>{intervieweeUrl}</code>
                        <button className="ghost" onClick={() => navigator.clipboard.writeText(intervieweeUrl)}>
                          복사
                        </button>
                      </p>
                    )}
                    {clientAccessId ? (
                      <p className="link-row">
                        클라이언트: <code>{clientAccessId}</code>
                        <button className="ghost" onClick={() => navigator.clipboard.writeText(clientAccessId)}>
                          복사
                        </button>
                      </p>
                    ) : (
                      <p className="link-row">
                        클라이언트: <span className="muted">프로젝트에 연결된 세션이 아닙니다</span>
                      </p>
                    )}
                  </>
                ) : (
                  <p className="muted small">참관 전용 — 링크는 PM만 볼 수 있습니다.</p>
                )}
              </div>
            </div>
          </div>

          <div className={`dock-panel ${activePanel === "options" ? "open" : ""}`}>
            <div className="hover-drawer-section">
              <div className="hover-drawer-label">• 세션 옵션</div>
              <div className="p-body">
                <p className="link-row">
                  인터뷰 시간: <strong>{session?.duration_minutes ?? "-"}분</strong>
                </p>
                <p className="link-row">
                  통역 언어:{" "}
                  <strong>
                    {LANGUAGE_LABELS[session?.interpretation_language ?? "ko"] ?? session?.interpretation_language}
                  </strong>
                </p>
                <p className="muted small">실시간 통역 반영은 아직 준비 중이며, 위 값은 세션 생성 시 선택한 설정입니다.</p>
              </div>
            </div>
          </div>
        </div>
        <span className="tlab">세션 상태 (미리보기)</span>
        <div className="swg">
          {(Object.keys(statusLabel) as Phase[]).map((p) => (
            <button
              key={p}
              type="button"
              className={phase === p ? "on" : ""}
              title="백엔드 연동 전 화면 미리보기용 — 연동 후엔 자동으로 반영됩니다"
              disabled={phase !== p}
            >
              {statusLabel[p]}
            </button>
          ))}
        </div>
      </div>
      <main className="monitor">
      <div className="col-transcript">
      <section className="panel">
        <header className="p-head">
          <div>
            <h2>응답자 화면</h2>
            <div className="sub status-line">
              <span>실시간 상태 · {phaseLabel}</span>
              <span className="timer-inline">
                <span className="dot" />
                {timerLabel}
              </span>
              <button type="button" className="btn-sm" disabled title="곧 지원 예정 · 백엔드 연동 후 사용 가능">
                ＋10분
              </button>
              <span className={`badge ${status}`}>{status}</span>
              {actionError && <span className="error-text" style={{ color: "red", fontSize: "12px", marginLeft: "8px" }}>{actionError}</span>}
            </div>
          </div>
        </header>

        <div className="resp-stage">
          {phase === "wait" && (
            <div>
              <b>인터뷰이 입장 대기 중</b>
              발급된 링크로 접속하면 응답자가 연결됩니다
            </div>
          )}
          {phase !== "wait" && (
            <>
              <span className="rs-badge">
                <span className="rs-dot" />
                응답자 {intervieweeOnline ? "접속중" : "연결 끊김"}
              </span>
              <div
                className="rs-figure"
                style={rtcCreds ? {
                  overflow: "hidden",
                  position: "relative",
                  width: "100%",
                  height: "100%",
                  borderRadius: "12px",
                  background: "#000"
                } : {
                  overflow: "hidden",
                  position: "relative"
                }}
              >
                {rtcCreds ? (
                  <VideoSubscriber token={rtcCreds.token} groupId={rtcCreds.group_id} onStreamReady={setRemoteStream} />
                ) : (
                  <svg viewBox="0 0 200 240" fill="none">
                    <ellipse cx="100" cy="74" rx="44" ry="48" fill="rgba(120,220,180,.2)" />
                    <path
                      d="M26 240 C26 174 60 138 100 138 C140 138 174 174 174 240 Z"
                      fill="rgba(120,220,180,.15)"
                    />
                  </svg>
                )}
              </div>
              <div className="rs-strip">
                {phase === "live" && (
                  <div className="wave me">
                    <span />
                    <span />
                    <span />
                    <span />
                  </div>
                )}
                <span className="rs-status">
                  {phase === "joined" && "입장함 · 인터뷰 시작 대기 중"}
                  {phase === "live" && "답변 중"}
                  {phase === "end" && "세션 종료됨"}
                </span>
                <div className="audio-seg">
                  <button type="button" className="on" disabled title="곧 지원 예정">
                    원문 음성
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        {phase !== "wait" && (
          <div className="caption-bar">
            {liveTextEn && (
              <div className="caption-line en">
                <span className="caption-tag en">EN 번역</span>
                <span className="caption-text">{liveTextEn}</span>
              </div>
            )}
            {liveTextKo && (
              <div className="caption-line ko">
                <span className="caption-tag ko">KO 원문</span>
                <span className="caption-text">{liveTextKo}</span>
              </div>
            )}
            {!liveTextKo && !liveTextEn && (
              <div className="caption-line placeholder">
                🎙️ 응답자가 발화하면 실시간 번역 및 원문 STT 자막이 여기에 표시됩니다.
              </div>
            )}
          </div>
        )}
      </section>
      </div>

      <div className="col-instructions">
        <section className="panel">
            <header className="p-head">
              <div>
                <h2>실시간 진행 상황</h2>
                <div className="sub">STT 변환 · AI 판단 · 질문/답변 순</div>
              </div>
              <div className="lang-toggle">
                <button type="button" className={!showTranslation ? "active" : ""} onClick={() => setShowTranslation(false)}>
                  원문
                </button>
                <button type="button" className={showTranslation ? "active" : ""} onClick={() => setShowTranslation(true)}>
                  원문+번역
                </button>
              </div>
            </header>

            <div className="turns">
              {transcript.map((turn) => (
                <article key={`${turn.speaker}-${turn.index}`} className={`turn ${turn.speaker}`}>
                  <div className="turn-head">
                    <strong>{turn.speaker === "assistant" ? "AI 진행자" : "응답자"}</strong>
                    <time>
                      {new Date(turn.created_at).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })}
                    </time>
                  </div>
                  <p>{turn.text}</p>
                  {showTranslation && turn.speaker === "interviewee" && (turn.text_en || translations[turn.index]) && (
                    <p className="turn-translation">{turn.text_en || translations[turn.index]}</p>
                  )}
                  {/* AI 판단 근거는 참관자에게만 보인다 (C5) */}
                  {turn.rationale && (
                    <div className="rationale">
                      <div className="ai-label">AI 판단 근거</div>
                      {turn.rationale}
                    </div>
                  )}
                </article>
              ))}
              {transcript.length === 0 && (
                <p className="empty">
                  {phase === "wait" && "인터뷰이가 입장하면 대화가 여기에 표시됩니다."}
                  {phase === "joined" && "인터뷰이가 입장했습니다. 첫 발화가 오면 진행됩니다."}
                  {(phase === "live" || phase === "end") && "아직 발화가 없습니다."}
                </p>
              )}
            </div>

            {phase === "end" && (
              <div className="report-note">
                {!report ? (
                  <>세션이 종료되었습니다. <b>AI 리포트</b>를 생성하고 있습니다 — 완료되면 아래에 표시됩니다.</>
                ) : (
                  <>
                    <b>AI 리포트</b>가 생성되었습니다.
                  </>
                )}
              </div>
            )}
            {report && (
              <div className="report-highlight" ref={reportRef}>
                {typeof report.data.summary === "string" && <p>{report.data.summary}</p>}
                <pre style={{ whiteSpace: "pre-wrap", margin: 0, fontSize: 11 }}>
                  {JSON.stringify(report.data, null, 2)}
                </pre>
              </div>
            )}
        </section>

        {role === "pm" && (
          <section className={`panel ${phase === "wait" || phase === "joined" ? "locked" : ""}`}>
            <button
              type="button"
              className="accordion-head"
              onClick={() => setInstructionsOpen((v) => !v)}
            >
              <div>
                <h2>실시간 지시</h2>
                <div className="sub">다음 질문에 반영 · 응답자에게 노출 안 됨</div>
              </div>
              <span className="accordion-caret">{instructionsOpen ? "▾" : "▸"}</span>
            </button>
            {instructionsOpen && (
              <>
                {phase === "end" ? (
                  <p className="muted small" style={{ padding: "10px 16px" }}>
                    세션이 종료되어 새 지시는 보낼 수 없습니다. 아래에서 지시 이력만 확인할 수 있습니다.
                  </p>
                ) : (
                  <>
                    <div className="composer p-body">
                      <textarea
                        rows={2}
                        value={draft}
                        placeholder="예) 경쟁사 대비 장점을 물어봐"
                        onChange={(event) => setDraft(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" && !event.shiftKey) {
                            event.preventDefault();
                            sendInstruction();
                          }
                        }}
                      />
                      <button onClick={sendInstruction} disabled={status !== "connected"}>
                        지시 보내기
                      </button>
                    </div>
                    <div className="quick">
                      {QUICK_INSTRUCTIONS.map((text) => (
                        <button key={text} onClick={() => setDraft(text)}>
                          {text}
                        </button>
                      ))}
                    </div>
                    <p className="muted small" style={{ padding: "6px 16px 10px" }}>
                      응답자의 다음 발화가 끝나면 1건씩 순서대로 주입됩니다.
                    </p>
                  </>
                )}

                <button
                  type="button"
                  className="accordion-head accordion-head--sub"
                  onClick={() => setHistoryOpen((v) => !v)}
                >
                  <h2>지시 이력</h2>
                  <span className="accordion-caret">{historyOpen ? "▾" : "▸"}</span>
                </button>
                {historyOpen && (
                  <div className="p-body">
                    <ul className="hist">
                      {instructions.map((instruction) => (
                        <li key={instruction.id} className="h-item">
                          <time>
                            {new Date(instruction.created_at).toLocaleTimeString("ko-KR", {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </time>
                          <span className={`h-dot ${instruction.status}`} />
                          <div className="h-body">
                            <div className={`h-state ${instruction.status}`}>
                              {instruction.status === "applied" ? "반영됨" : "대기 중"}
                            </div>
                            <div className="h-text">{instruction.text}</div>
                          </div>
                        </li>
                      ))}
                      {instructions.length === 0 && <p className="empty">아직 보낸 지시가 없습니다.</p>}
                    </ul>
                  </div>
                )}
              </>
            )}
          </section>
        )}
      </div>
      </main>

      {editModalOpen && (
        <div className="modal-bg" onClick={() => setEditModalOpen(false)}>
          <div className="modal" onClick={(event) => event.stopPropagation()}>
            <h2>질문 편집</h2>
            <p className="m-sub">파일로 질문지를 가져올 형식을 선택하세요</p>

            <div className="format-seg">
              {FILE_FORMATS.map((format) => (
                <button
                  key={format.key}
                  type="button"
                  className={fileFormat === format.key ? "on" : ""}
                  onClick={() => {
                    setFileFormat(format.key);
                    setSelectedFile(null);
                  }}
                >
                  {format.label}
                </button>
              ))}
            </div>

            <input
              type="file"
              accept={FILE_FORMATS.find((f) => f.key === fileFormat)?.accept}
              onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
            />
            {selectedFile && <p className="muted small">선택된 파일: {selectedFile.name}</p>}

            <p className="m-hint">
              업로드한 문서를 AI가 자동 분석하여 실시간 질문 트리(JSON) 구조로 변환합니다.
            </p>

            <div className="modal-actions">
              <button type="button" className="btn-ghost" onClick={() => setEditModalOpen(false)}>
                취소
              </button>
              <button
                type="button"
                disabled={!selectedFile || uploadingGuide}
                onClick={async () => {
                  if (!selectedFile) return;
                  setUploadingGuide(true);
                  try {
                    const result = await uploadGuideFile(selectedFile);
                    alert(`✅ 가이드라인 분석 완료!\n주제: ${result.study.title}\n추출된 질문 수: ${result.study.questions.length}개`);
                    if (session) {
                      setSession({
                        ...session,
                        questions: result.study.questions,
                      });
                    }
                    setEditModalOpen(false);
                  } catch (e: any) {
                    alert(`❌ 업로드 실패: ${e.message}`);
                  } finally {
                    setUploadingGuide(false);
                  }
                }}
              >
                {uploadingGuide ? "AI 파싱 중…" : "적용"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
