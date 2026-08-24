import { useSelfViewStream } from "../hooks/useSelfViewStream";
import MicButton from "./MicButton";

interface RespondentMonitorProps {
  /** running 단계에서만 카메라를 켠다. */
  isActive: boolean;
  isRecording: boolean;
  onRecordingChange: (isRecording: boolean) => void;
  showMicOffAlert: boolean;
  onAudioChunk?: (base64PCM: string) => void;
  onRecordingStart?: () => void;
  onRecordingStop?: () => void;
  onEndInterview?: () => void;
}

export default function RespondentMonitor({
  isActive,
  isRecording,
  onRecordingChange,
  showMicOffAlert,
  onAudioChunk,
  onRecordingStart,
  onRecordingStop,
  onEndInterview,
}: RespondentMonitorProps) {
  const { videoRef, isCameraOn } = useSelfViewStream(isActive);

  return (
    <section className="monitor monitor-self">
      {/* 상단 바: 좌측에 나 (응답자) 라벨, 우측에 빨간색 인터뷰 종료 버튼 */}
      <div className="monitor-top-bar">
        <span className="monitor-tag">나 (응답자)</span>
        {onEndInterview && (
          <button
            onClick={onEndInterview}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "5px",
              background: "rgba(239, 68, 68, 0.2)",
              border: "1px solid rgba(239, 68, 68, 0.6)",
              color: "#fca5a5",
              fontSize: "0.75rem",
              fontWeight: 600,
              padding: "4px 12px",
              borderRadius: "14px",
              cursor: "pointer",
              backdropFilter: "blur(8px)",
              transition: "all 0.2s ease",
              boxShadow: "0 2px 10px rgba(239, 68, 68, 0.25)",
            }}
            title="인터뷰를 종료하고 퇴장합니다"
          >
            <span>🚪</span>
            <span>인터뷰 종료</span>
          </button>
        )}
      </div>

      <div className="self-video-wrapper">
        <video
          ref={videoRef}
          className="self-video"
          autoPlay
          playsInline
          muted
        />
        {!isCameraOn && (
          <div className="self-fallback">
            <span className="self-fallback-icon">📷</span>
            <p>카메라를 불러오는 중입니다</p>
          </div>
        )}
      </div>

      <div className={`mic-banner ${showMicOffAlert ? "warning" : ""}`}>
        <MicButton
          isRecording={isRecording}
          onRecordingChange={onRecordingChange}
          onAudioChunk={onAudioChunk}
          onRecordingStart={onRecordingStart}
          onRecordingStop={onRecordingStop}
        />
        <div className="mic-banner-content">
          {showMicOffAlert ? (
            <p className="mic-banner-warning">
              🎤 마이크가 꺼져 있어요 — 답변하려면 마이크 버튼을 눌러주세요
            </p>
          ) : (
            <p className="mic-banner-guide">
              마이크를 켠 뒤 편하게 답변해 주세요.<br />
              답변을 마치면 버튼을 한 번 더 눌러 주세요.
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
