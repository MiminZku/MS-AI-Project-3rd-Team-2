import { useEffect, useRef, useState } from "react";
import type { Role } from "../App";
import { endSession, fetchReport, observerSocketUrl } from "../api";
import { DEMO_INSTRUCTIONS, DEMO_REPORT, DEMO_SESSION, DEMO_SESSION_ID, DEMO_TRANSCRIPT } from "../demoData";
import type { Instruction, Report, ServerMessage, Session, Turn } from "../types";

interface Props {
  sessionId: string;
  intervieweeUrl: string;
  role: Role;
}

interface Timekeeper {
  should_move_on: boolean;
  remaining_minutes: number;
  remaining_questions: number;
  hint: string;
}

type Phase = "wait" | "joined" | "live" | "end";

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

export default function Monitor({ sessionId, intervieweeUrl, role }: Props) {
  const [session, setSession] = useState<Session | null>(null);
  const [transcript, setTranscript] = useState<Turn[]>([]);
  const [instructions, setInstructions] = useState<Instruction[]>([]);
  const [timekeeper, setTimekeeper] = useState<Timekeeper | null>(null);
  const [intervieweeOnline, setIntervieweeOnline] = useState(false);
  const [status, setStatus] = useState("connecting");
  const [draft, setDraft] = useState("");
  const [report, setReport] = useState<Report | null>(null);
  const [ending, setEnding] = useState(false);
  const [elapsedSec, setElapsedSec] = useState(0);
  const socketRef = useRef<WebSocket | null>(null);

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

  return (
    <main className="monitor">
      <section className="panel col-questions">
        <h2 style={{ padding: "13px 16px 0" }}>질문 트리</h2>
        <ol className="tree">
          {questions.map((question, index) => (
            <li key={question.id} className={index === session?.current_question_index ? "current" : ""}>
              {question.text}
              {Object.entries(question.branches).map(([condition, followUp]) => (
                <div key={condition} className="branch">
                  <span className="cond">{condition}</span>
                  {followUp}
                </div>
              ))}
            </li>
          ))}
        </ol>

        {timekeeper && (
          <div className={`timekeeper ${timekeeper.should_move_on ? "warn" : ""}`} style={{ margin: "0 16px 16px" }}>
            <strong>타임키퍼</strong>
            <p>{timekeeper.hint}</p>
          </div>
        )}
      </section>

      <section className="panel col-transcript">
        <header className="panel-head">
          <h2>실시간 대화</h2>
          <span className="timer">
            <span className="dot" />
            <b>{timerLabel}</b>
            <small>{phaseLabel}</small>
          </span>
          <span className={`badge ${status}`}>{status}</span>
          <span className={`badge ${intervieweeOnline ? "connected" : ""}`}>
            응답자 {intervieweeOnline ? "접속중" : "대기"}
          </span>
          {role === "pm" && phase === "live" && (
            <button
              className="sess-btn stop"
              disabled={ending}
              onClick={async () => {
                setEnding(true);
                if (sessionId === DEMO_SESSION_ID) {
                  const endedAt = new Date().toISOString();
                  setSession((prev) => (prev ? { ...prev, status: "ended", ended_at: endedAt } : prev));
                  setTimeout(() => setReport(DEMO_REPORT), 1500);
                } else {
                  await endSession(sessionId).catch(() => undefined);
                }
                setEnding(false);
              }}
            >
              인터뷰 종료
            </button>
          )}
        </header>

        {intervieweeUrl && role === "pm" && (
          <p className="link-row" style={{ margin: "12px 16px 0" }}>
            응답자 링크: <code>{intervieweeUrl}</code>
            <button className="ghost" onClick={() => navigator.clipboard.writeText(intervieweeUrl)}>
              복사
            </button>
          </p>
        )}

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
              {phase === "joined" && <div>입장함 · 인터뷰 시작 대기 중</div>}
              {phase === "live" && <div>답변 중</div>}
              {phase === "end" && <div>세션 종료됨</div>}
            </>
          )}
        </div>

        <div className="turns">
          {transcript.map((turn) => (
            <article key={`${turn.speaker}-${turn.index}`} className={`turn ${turn.speaker}`}>
              <strong>{turn.speaker === "assistant" ? "AI 진행자" : "응답자"}</strong>
              <p>{turn.text}</p>
              {/* AI 판단 근거는 참관자에게만 보인다 (C5) */}
              {turn.rationale && <p className="rationale">AI 판단 근거: {turn.rationale}</p>}
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
          <div className="report-highlight">
            {typeof report.data.summary === "string" && <p>{report.data.summary}</p>}
            <pre style={{ whiteSpace: "pre-wrap", margin: 0, fontSize: 11 }}>
              {JSON.stringify(report.data, null, 2)}
            </pre>
          </div>
        )}
      </section>

      <section className="panel col-instructions">
        {role === "pm" ? (
          <>
            <h2 style={{ padding: "13px 16px 0" }}>실시간 지시</h2>
            <div className={`composer p-body ${phase !== "live" ? "locked" : ""}`}>
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
            <p className="muted small" style={{ padding: "10px 16px 0" }}>
              응답자의 다음 발화가 끝나면 1건씩 순서대로 주입됩니다.
            </p>

            <ul className="instructions">
              {instructions.map((instruction) => (
                <li key={instruction.id} className={instruction.status}>
                  <span className="status">{instruction.status === "applied" ? "반영됨" : "대기 중"}</span>
                  {instruction.text}
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p className="empty">참관 전용 화면입니다.</p>
        )}
      </section>
    </main>
  );
}
