import Orb from "./Orb";
import { AvatarConnectionStatus } from "../hooks/useAvatarWebRTC";

interface AvatarMonitorProps {
  videoRef?: React.Ref<HTMLVideoElement>;
  status?: AvatarConnectionStatus;
  orbState?: "idle" | "speaking" | "listening";
  errorMessage?: string | null;
  onRetry?: () => void;
}

export default function AvatarMonitor({
  videoRef,
  status = "connected",
  orbState = "idle",
  errorMessage,
  onRetry,
}: AvatarMonitorProps) {
  const isWebRTCActive = status === "connected" || status === "speaking";

  return (
    <section className="monitor monitor-avatar" style={{ position: "relative", overflow: "hidden" }}>
      <div className="monitor-header" style={{ position: "absolute", top: 12, left: 12, zIndex: 10, display: "flex", gap: 8, alignItems: "center" }}>
        <span className="monitor-tag">AI 모더레이터</span>
        {status === "connecting" && (
          <span style={{ fontSize: "0.75rem", background: "rgba(0,0,0,0.6)", color: "#60a5fa", padding: "2px 8px", borderRadius: 4 }}>
            아바타 연결 중...
          </span>
        )}
        {status === "speaking" && (
          <span style={{ fontSize: "0.75rem", background: "rgba(34,197,94,0.8)", color: "#fff", padding: "2px 8px", borderRadius: 4 }}>
            말하는 중 🎙️
          </span>
        )}
        {status === "error" && (
          <span style={{ fontSize: "0.75rem", background: "rgba(239,68,68,0.8)", color: "#fff", padding: "2px 8px", borderRadius: 4 }}>
            연결 오류
          </span>
        )}
      </div>

      {/* 실시간 아바타 비디오 스트림 */}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          display: isWebRTCActive ? "block" : "none",
        }}
      />

      {/* 아바타 연결 전 또는 에러 시 Orb/안내문구 표시 */}
      {!isWebRTCActive && (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 16 }}>
          <Orb status={status === "connecting" ? "listening" : orbState} />
          {status === "connecting" && (
            <p style={{ color: "#94a3b8", fontSize: "0.875rem" }}>Azure 아바타 세션을 준비하고 있습니다...</p>
          )}
          {status === "error" && (
            <div style={{ textAlign: "center" }}>
              <p style={{ color: "#f87171", fontSize: "0.875rem", marginBottom: 8 }}>
                {errorMessage || "아바타 연결에 실패했습니다."}
              </p>
              {onRetry && (
                <button
                  onClick={onRetry}
                  style={{
                    background: "#3b82f6",
                    color: "white",
                    border: "none",
                    padding: "6px 14px",
                    borderRadius: "6px",
                    cursor: "pointer",
                    fontSize: "0.875rem",
                  }}
                >
                  다시 연결
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
