import { useSelfViewStream } from "../hooks/useSelfViewStream";
import MicButton from "./MicButton";

interface RespondentMonitorProps {
  /** running 단계에서만 카메라를 켠다. */
  isActive: boolean;
  isRecording: boolean;
  onRecordingChange: (isRecording: boolean) => void;
  showMicOffAlert: boolean;
}

export default function RespondentMonitor({
  isActive,
  isRecording,
  onRecordingChange,
  showMicOffAlert,
}: RespondentMonitorProps) {
  const { videoRef, isCameraOn } = useSelfViewStream(isActive);

  return (
    <section className="monitor monitor-self">
      <span className="monitor-tag">나 (응답자)</span>

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
        <MicButton isRecording={isRecording} onRecordingChange={onRecordingChange} />
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
