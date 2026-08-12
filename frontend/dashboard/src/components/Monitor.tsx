import { useEffect, useRef, useState } from "react";
import { observerSocketUrl } from "../api";
import type { Instruction, ServerMessage, Session, Turn } from "../types";

interface Props {
  sessionId: string;
  intervieweeUrl: string;
}

interface Timekeeper {
  should_move_on: boolean;
  remaining_minutes: number;
  remaining_questions: number;
  hint: string;
}

export default function Monitor({ sessionId, intervieweeUrl }: Props) {
  const [session, setSession] = useState<Session | null>(null);
  const [transcript, setTranscript] = useState<Turn[]>([]);
  const [instructions, setInstructions] = useState<Instruction[]>([]);
  const [timekeeper, setTimekeeper] = useState<Timekeeper | null>(null);
  const [intervieweeOnline, setIntervieweeOnline] = useState(false);
  const [status, setStatus] = useState("connecting");
  const [draft, setDraft] = useState("");
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
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

  const sendInstruction = () => {
    const text = draft.trim();
    const socket = socketRef.current;
    if (!text || socket?.readyState !== WebSocket.OPEN) return;
    socket.send(JSON.stringify({ type: "instruction.create", text }));
    setDraft("");
  };

  const questions = session?.questions ?? [];

  return (
    <main className="monitor">
      <section className="panel col-questions">
        <h2>질문 트리</h2>
        <ol className="tree">
          {questions.map((question, index) => (
            <li
              key={question.id}
              className={index === session?.current_question_index ? "current" : ""}
            >
              {question.text}
              {Object.entries(question.branches).map(([condition, followUp]) => (
                <div key={condition} className="branch">
                  <span className="cond">[{condition}]</span> {followUp}
                </div>
              ))}
            </li>
          ))}
        </ol>

        {timekeeper && (
          <div className={`timekeeper ${timekeeper.should_move_on ? "warn" : ""}`}>
            <strong>타임키퍼</strong>
            <p>{timekeeper.hint}</p>
          </div>
        )}
      </section>

      <section className="panel col-transcript">
        <header className="panel-head">
          <h2>실시간 대화</h2>
          <span className={`badge ${status}`}>{status}</span>
          <span className={`badge ${intervieweeOnline ? "connected" : ""}`}>
            응답자 {intervieweeOnline ? "접속중" : "대기"}
          </span>
        </header>

        {intervieweeUrl && (
          <p className="link-row">
            응답자 링크: <code>{intervieweeUrl}</code>
            <button className="ghost" onClick={() => navigator.clipboard.writeText(intervieweeUrl)}>
              복사
            </button>
          </p>
        )}

        <div className="turns">
          {transcript.map((turn) => (
            <article key={`${turn.speaker}-${turn.index}`} className={`turn ${turn.speaker}`}>
              <strong>{turn.speaker === "assistant" ? "AI 진행자" : "응답자"}</strong>
              <p>{turn.text}</p>
              {/* AI 판단 근거는 참관자에게만 보인다 (C5) */}
              {turn.rationale && <p className="rationale">판단 근거: {turn.rationale}</p>}
            </article>
          ))}
        </div>
      </section>

      <section className="panel col-instructions">
        <h2>실시간 지시</h2>
        <div className="composer">
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
        <p className="muted small">응답자의 다음 발화가 끝나면 1건씩 순서대로 주입됩니다.</p>

        <ul className="instructions">
          {instructions.map((instruction) => (
            <li key={instruction.id} className={instruction.status}>
              <span className="status">{instruction.status}</span>
              {instruction.text}
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
