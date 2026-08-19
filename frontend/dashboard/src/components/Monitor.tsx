import { useCallback, useEffect, useRef, useState } from "react";
import type { Role } from "../App";
import { endSession, fetchReport, observerSocketUrl, fetchRtcToken } from "../api";
import { DEMO_INSTRUCTIONS, DEMO_REPORT, DEMO_SESSION, DEMO_SESSION_ID, DEMO_TRANSCRIPT } from "../demoData";
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
  ending: boolean;
  hasReport: boolean;
  onEndSession: () => void;
  onOpenReport: () => void;
}

const QUICK_INSTRUCTIONS = [
  "방금 답변을 더 구체적으로 캐물어봐 주세요.",
  "경쟁 앱과 비교해서 물어봐 주세요.",
  "다음 주제로 자연스럽게 넘어가 주세요.",
];

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
  const [report, setReport] = useState<Report | null>(null);
  const [ending, setEnding] = useState(false);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [rtcCreds, setRtcCreds] = useState<{ token: string; group_id: string } | null>(null);
  // 백엔드가 세션 상태를 자동으로 넘겨주기 전까지, 화면 미리보기용 수동 오버라이드.
  const [previewPhase, setPreviewPhase] = useState<Phase | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [activePanel, setActivePanel] = useState<"tree" | "links" | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const reportRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (sessionId !== DEMO_SESSION_ID) {
      fetchRtcToken(sessionId)
        .then(creds => setRtcCreds(creds))
        .catch(err => console.error("ACS token fetch failed", err));
    }
  }, [sessionId]);

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
        case "session.snapshot":
          setSession(message.session);
          setTranscript(message.transcript);
          setInstructions(message.instructions);
          setIntervieweeOnline(message.interviewee_connected);
          break;
        case "transcript.append":
          setTranscript((prev) => [...prev, message.turn]);
          if (message.turn.speaker === "interviewee") {
            setLiveTextKo("");
            setLiveTextEn("");
          }
          break;
        case "transcript.partial":
          if (message.lang === "ko") setLiveTextKo(message.text);
          if (message.lang === "en") setLiveTextEn(message.text);
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

  const sendInstruction = () => {
    const text = draft.trim();
    const socket = socketRef.current;
    if (!text || socket?.readyState !== WebSocket.OPEN) return;
    socket.send(JSON.stringify({ type: "instruction.create", text }));
    setDraft("");
  };

  const handleEndSession = useCallback(async () => {
    setEnding(true);
    if (sessionId === DEMO_SESSION_ID) {
      const endedAt = new Date().toISOString();
      setSession((prev) => (prev ? { ...prev, status: "ended", ended_at: endedAt } : prev));
      setTimeout(() => setReport(DEMO_REPORT), 1500);
    } else {
      await endSession(sessionId).catch(() => undefined);
    }
    setEnding(false);
  }, [sessionId]);

  const handleOpenReport = useCallback(() => {
    reportRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const phase = previewPhase ?? phaseOf(session, intervieweeOnline);
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
      ending,
      hasReport: report != null,
      onEndSession: handleEndSession,
      onOpenReport: handleOpenReport,
    });
  }, [role, phase, ending, report, handleEndSession, handleOpenReport, onStatusChange]);

  // Monitor가 언마운트될 때만(세션 목록으로 돌아갈 때) 상단바 상태를 지운다.
  useEffect(() => () => onStatusChange?.(null), [onStatusChange]);

  return (
    <>
      <div className="tabbar">
        <span className="tlab">세션 상태 (미리보기)</span>
        <div className="swg">
          {(Object.keys(statusLabel) as Phase[]).map((p) => (
            <button
              key={p}
              type="button"
              className={phase === p ? "on" : ""}
              title="백엔드 연동 전 화면 미리보기용 — 연동 후엔 자동으로 반영됩니다"
              onClick={() => setPreviewPhase(p)}
            >
              {statusLabel[p]}
            </button>
          ))}
        </div>
        <div className="kebab-wrap">
          <button
            type="button"
            className="kebab-btn"
            title="질문 트리 / 세션 링크"
            onClick={() => setMenuOpen((v) => !v)}
          >
            ⋮
          </button>
          {menuOpen && (
            <>
              <button
                type="button"
                className="kebab-backdrop"
                aria-label="메뉴 닫기"
                onClick={() => setMenuOpen(false)}
              />
              <div className="kebab-menu">
                <button
                  type="button"
                  onClick={() => {
                    setActivePanel("tree");
                    setMenuOpen(false);
                  }}
                >
                  질문 트리
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setActivePanel("links");
                    setMenuOpen(false);
                  }}
                >
                  세션 링크
                </button>
              </div>
            </>
          )}
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
              <span className={`badge ${status}`}>{status}</span>
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
                  aspectRatio: "16 / 9", 
                  height: "auto", 
                  borderRadius: "12px", 
                  background: "#000" 
                } : { 
                  overflow: "hidden", 
                  position: "relative" 
                }}
              >
                {rtcCreds ? (
                  <VideoSubscriber token={rtcCreds.token} groupId={rtcCreds.group_id} />
                ) : (
                  <svg viewBox="0 0 200 240" fill="none">
                    <ellipse cx="100" cy="74" rx="44" ry="48" fill="rgba(120,220,180,.2)" />
                    <path
                      d="M26 240 C26 174 60 138 100 138 C140 138 174 174 174 240 Z"
                      fill="rgba(120,220,180,.15)"
                    />
                  </svg>
                )}
                {/* 실시간 자막 UI */}
                {(liveTextKo || liveTextEn) && (
                  <div style={{ position: "absolute", bottom: "16px", left: "16px", right: "16px", background: "rgba(0,0,0,0.7)", color: "white", padding: "12px", borderRadius: "8px", fontSize: "14px", lineHeight: 1.5, zIndex: 10 }}>
                    {liveTextKo && <div style={{ marginBottom: liveTextEn ? "4px" : 0 }}>{liveTextKo}</div>}
                    {liveTextEn && <div style={{ color: "#ffd54f" }}>{liveTextEn}</div>}
                  </div>
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
                  <button type="button" disabled title="곧 지원 예정">
                    통역 음성
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </section>
      </div>

      {role === "pm" && (
        <div className="col-instructions">
          <section className={`panel ${phase !== "live" ? "locked" : ""}`}>
            <header className="p-head">
              <div>
                <h2>실시간 지시</h2>
                <div className="sub">다음 질문에 반영 · 응답자에게 노출 안 됨</div>
              </div>
            </header>
            <div className="composer p-body">
              <textarea
                rows={3}
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
            <p className="muted small" style={{ padding: "10px 16px 16px" }}>
              응답자의 다음 발화가 끝나면 1건씩 순서대로 주입됩니다.
            </p>

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
          </section>

          <section className="panel">
            <header className="p-head">
              <div>
                <h2>실시간 진행 상황</h2>
                <div className="sub">STT 변환 · AI 판단 · 질문/답변 순</div>
              </div>
              <div className="lang-toggle">
                <button type="button" className="active" disabled title="곧 지원 예정">
                  원문
                </button>
                <button type="button" disabled title="곧 지원 예정">
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
        </div>
      )}
      </main>

      {activePanel && (
        <>
          <button
            type="button"
            className="overlay-backdrop"
            aria-label="패널 닫기"
            onClick={() => setActivePanel(null)}
          />
          <div className="overlay-panel">
            <div className="overlay-panel-head">
              <h2>{activePanel === "tree" ? "질문 트리" : "세션 링크"}</h2>
              <button type="button" className="overlay-close" onClick={() => setActivePanel(null)}>
                ×
              </button>
            </div>

            {activePanel === "tree" && (
              <div className="overlay-panel-body">
                <div className="accordion-actions">
                  {role === "pm" ? (
                    <button type="button" className="btn-sm solid" disabled title="곧 지원 예정">
                      ＋ 질문 편집
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
                          {Object.entries(question.branches).map(([condition, followUp]) => (
                            <div key={condition} className="branch">
                              <span className="cond">{condition}</span>
                              {followUp}
                            </div>
                          ))}
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
            )}

            {activePanel === "links" && (
              <div className="overlay-panel-body p-body">
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
                    <p className="link-row">
                      클라이언트: <span className="muted">준비 중</span>
                    </p>
                  </>
                ) : (
                  <p className="muted small">참관 전용 — 링크는 PM만 볼 수 있습니다.</p>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </>
  );
}
