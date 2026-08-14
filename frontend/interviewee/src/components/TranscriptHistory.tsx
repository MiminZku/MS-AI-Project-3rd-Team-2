import type { Turn } from "../types";

interface TranscriptHistoryProps {
  history: Turn[];
}

export default function TranscriptHistory({ history }: TranscriptHistoryProps) {
  if (history.length === 0) return null;

  return (
    <section className="history-section glass-panel">
      <h3>💬 대화 기록</h3>
      <div className="transcript-list">
        {history.map((turn) => {
          const isAssistant = turn.speaker === "assistant";
          return (
            <div
              key={`${turn.speaker}-${turn.index}`}
              className={`transcript-bubble ${isAssistant ? "assistant" : "interviewee"}`}
            >
              <div className="bubble-header">
                <span className="speaker-name">{isAssistant ? "🤖 AI 면접관" : "👤 나"}</span>
                <span className="timestamp">
                  {turn.created_at ? new Date(turn.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ""}
                </span>
              </div>
              <div className="bubble-content">{turn.text}</div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
