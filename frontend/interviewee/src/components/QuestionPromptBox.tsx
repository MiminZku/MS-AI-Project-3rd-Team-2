
interface QuestionPromptBoxProps {
  question: string;
  onReplay?: () => void;
  isSpeaking?: boolean;
}

export default function QuestionPromptBox({
  question,
  onReplay,
  isSpeaking = false,
}: QuestionPromptBoxProps) {
  return (
    <section className="question-prompt-box">
      <div className="question-box">
        <p className="question-bubble">
          {question || "질문을 준비하고 있습니다..."}
        </p>

        {onReplay && (
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              marginTop: "8px",
            }}
          >
            <button
              onClick={onReplay}
              disabled={isSpeaking}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
                padding: "3px 8px",
                fontSize: "0.75rem",
                color: isSpeaking ? "#94a3b8" : "#93c5fd",
                background: "rgba(59, 130, 246, 0.15)",
                border: "1px solid rgba(96, 165, 250, 0.25)",
                borderRadius: "6px",
                cursor: isSpeaking ? "not-allowed" : "pointer",
                transition: "all 0.2s ease",
              }}
              title="아바타가 현재 질문을 음성으로 다시 읽어줍니다."
            >
              <span>🔊</span>
              <span>{isSpeaking ? "말하는 중..." : "다시듣기"}</span>
            </button>
          </div>
        )}
      </div>
    </section>
  );
}
