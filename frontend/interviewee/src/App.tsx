import { useEffect, useRef, useState } from "react";
import { WS_BASE_URL, sessionIdFromUrl } from "./config";
import type { ServerMessage, Turn } from "./types";

type Status = "idle" | "connecting" | "connected" | "closed" | "error";

/**
 * 응답자 화면.
 *
 * 현재는 STT/TTS 연결 전 단계라 텍스트 입력으로 발화를 대신한다.
 * MVP에서 교체할 지점:
 *   - 입력창 -> MediaRecorder 녹음 + endpointing(C2) -> 오디오 프레임 전송
 *   - 질문 표시 -> Azure TTS Avatar 재생 (실패 시 오브 폴백, C6)
 * 참관자의 존재/판단근거는 이 화면에 절대 나타나면 안 된다 (C5).
 */
export default function App() {
  const [sessionId] = useState(sessionIdFromUrl);
  const [status, setStatus] = useState<Status>("idle");
  const [title, setTitle] = useState("");
  const [question, setQuestion] = useState("연결하면 인터뷰가 시작됩니다.");
  const [history, setHistory] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const socketRef = useRef<WebSocket | null>(null);

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
      } else if (message.type === "assistant.question") {
        setQuestion(message.turn.text);
        setHistory((prev) => [...prev, message.turn]);
        // TODO(MVP): 여기서 TTS/아바타 재생을 트리거한다.
      } else if (message.type === "error") {
        setQuestion(`오류: ${message.message}`);
      }
    };

    return () => socket.close();
  }, [sessionId]);

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
  };

  if (!sessionId) {
    return (
      <main className="shell">
        <h1>인터뷰 링크가 필요합니다</h1>
        <p className="muted">담당자가 보내드린 링크(?session=...)로 접속해주세요.</p>
      </main>
    );
  }

  return (
    <main className="shell">
      <header>
        <h1>{title || "AI 인터뷰"}</h1>
        <span className={`badge ${status}`}>{status}</span>
      </header>

      <section className="stage">
        {/* TODO(D7): 이 자리에 TTS Avatar 비디오 / 오브 폴백을 렌더링 */}
        <div className="orb" aria-hidden />
        <p className="question">{question}</p>
      </section>

      <section className="composer">
        <textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              send();
            }
          }}
          placeholder="답변을 입력하세요 (STT 연결 전 임시 입력)"
          rows={3}
        />
        <button onClick={send} disabled={status !== "connected"}>
          보내기
        </button>
      </section>

      <section className="history">
        {history.map((turn) => (
          <p key={`${turn.speaker}-${turn.index}`} className={turn.speaker}>
            <strong>{turn.speaker === "assistant" ? "진행자" : "나"}</strong> {turn.text}
          </p>
        ))}
      </section>
    </main>
  );
}
