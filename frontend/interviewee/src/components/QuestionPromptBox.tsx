
interface QuestionPromptBoxProps {
  question: string;
  speechSpeed?: number;
  onSpeedChange?: (speed: number) => void;
  onReplay?: () => void;
  isSpeaking?: boolean;
}

export const SPEED_OPTIONS = [
  { value: 0.8, label: "0.8x (느림)" },
  { value: 1.0, label: "1.0x (보통)" },
  { value: 1.2, label: "1.2x (조금 빠름)" },
  { value: 1.35, label: "1.4x (빠름 · 추천)" },
  { value: 1.6, label: "1.6x (매우 빠름)" },
];

export default function QuestionPromptBox({
  question,
  speechSpeed = 1.35,
  onSpeedChange,
  onReplay,
  isSpeaking = false,
}: QuestionPromptBoxProps) {
  return (
    <section className="question-prompt-box">
      <div className="question-box" style={{ position: "relative" }}>
        <p className="question-bubble">
          {question || "질문을 준비하고 있습니다..."}
        </p>

        {/* 접근성 & 포용성 컨트롤 바 (다시듣기 + 유튜브 스타일 음성 속도 조절) */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-end",
            gap: "10px",
            marginTop: "10px",
            paddingTop: "8px",
            borderTop: "1px solid rgba(255, 255, 255, 0.1)",
          }}
        >
          {/* 질문 다시듣기 버튼 */}
          {onReplay && (
            <button
              onClick={onReplay}
              disabled={isSpeaking}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 12px",
                fontSize: "0.85rem",
                fontWeight: 500,
                color: isSpeaking ? "#94a3b8" : "#ffffff",
                background: isSpeaking ? "rgba(255, 255, 255, 0.08)" : "rgba(59, 130, 246, 0.3)",
                border: "1px solid rgba(96, 165, 250, 0.4)",
                borderRadius: "8px",
                cursor: isSpeaking ? "not-allowed" : "pointer",
                transition: "all 0.2s ease",
              }}
              title="아바타가 현재 질문을 음성으로 다시 읽어줍니다."
            >
              <span>🔊</span>
              <span>{isSpeaking ? "말하는 중..." : "질문 다시듣기"}</span>
            </button>
          )}

          {/* 유튜브 스타일 음성 속도 조절 드롭다운 */}
          {onSpeedChange && (
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                background: "rgba(0, 0, 0, 0.35)",
                border: "1px solid rgba(255, 255, 255, 0.15)",
                borderRadius: "8px",
                padding: "4px 8px",
              }}
            >
              <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>속도:</span>
              <select
                value={speechSpeed}
                onChange={(e) => onSpeedChange(parseFloat(e.target.value))}
                style={{
                  background: "transparent",
                  color: "#60a5fa",
                  fontSize: "0.85rem",
                  fontWeight: 600,
                  border: "none",
                  outline: "none",
                  cursor: "pointer",
                }}
                title="아바타 음성 발화 속도를 조절합니다."
              >
                {SPEED_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value} style={{ background: "#1e293b", color: "#fff" }}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
