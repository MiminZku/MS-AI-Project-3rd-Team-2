import { useEffect, useRef, useState } from "react";
import Orb from "./Orb";
import { AvatarConnectionStatus } from "../hooks/useAvatarWebRTC";

interface AvatarMonitorProps {
  videoRef?: React.Ref<HTMLVideoElement>;
  status?: AvatarConnectionStatus;
  orbState?: "idle" | "speaking" | "listening";
  errorMessage?: string | null;
  onRetry?: () => void;
}

const BACKGROUND_OPTIONS = [
  { id: "bg1", label: "내추럴 우드", icon: "🌿", url: "/bg1.jpg" },
  { id: "bg2", label: "모던 화이트", icon: "🏛️", url: "/bg2.jpg" },
  { id: "bg3", label: "클래식 서재", icon: "📚", url: "/bg3.jpg" },
  { id: "bg4", label: "나이트 시티", icon: "🌃", url: "/bg4.jpg" },
  { id: "bg5", label: "코지 룸", icon: "☕", url: "/bg5.jpg" },
];

export default function AvatarMonitor({
  videoRef,
  status = "connected",
  orbState = "idle",
  errorMessage,
  onRetry,
}: AvatarMonitorProps) {
  const isWebRTCActive = status === "connected" || status === "speaking";
  const [selectedBg, setSelectedBg] = useState<string>(() => {
    return localStorage.getItem("gromit_avatar_bg") || "/bg1.jpg";
  });
  const [isBgMenuOpen, setIsBgMenuOpen] = useState(false);

  const handleSelectBg = (url: string) => {
    setSelectedBg(url);
    localStorage.setItem("gromit_avatar_bg", url);
    setIsBgMenuOpen(false);
  };

  const internalVideoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const tmpCanvasRef = useRef<HTMLCanvasElement | null>(null);

  // 부모 videoRef와 internalVideoRef 동기화
  const setCombinedVideoRef = (node: HTMLVideoElement | null) => {
    internalVideoRef.current = node;
    if (typeof videoRef === "function") {
      videoRef(node);
    } else if (videoRef && typeof videoRef === "object" && "current" in videoRef) {
      (videoRef as React.MutableRefObject<HTMLVideoElement | null>).current = node;
    }
  };

  // 실시간 크로마키(Canvas Matting) 렌더링 루프
  useEffect(() => {
    if (!isWebRTCActive) return;

    let animFrameId: number;
    let lastTime = 0;

    const renderMatting = (timestamp: number) => {
      // 30fps로 스로틀링하여 브라우저 CPU 부하 최소화
      if (timestamp - lastTime > 30) {
        lastTime = timestamp;
        const video = internalVideoRef.current;
        const canvas = canvasRef.current;
        const tmpCanvas = tmpCanvasRef.current;

        if (video && canvas && tmpCanvas && video.videoWidth > 0) {
          const vw = video.videoWidth;
          const vh = video.videoHeight;

          if (tmpCanvas.width !== vw || tmpCanvas.height !== vh) {
            tmpCanvas.width = vw;
            tmpCanvas.height = vh;
          }
          if (canvas.width !== vw || canvas.height !== vh) {
            canvas.width = vw;
            canvas.height = vh;
          }

          const tmpCtx = tmpCanvas.getContext("2d", { willReadFrequently: true });
          const mainCtx = canvas.getContext("2d");

          if (tmpCtx && mainCtx) {
            tmpCtx.drawImage(video, 0, 0, vw, vh);
            const frame = tmpCtx.getImageData(0, 0, vw, vh);
            const data = frame.data;
            const len = data.length / 4;

            for (let i = 0; i < len; i++) {
              const r = data[i * 4 + 0];
              const g = data[i * 4 + 1];
              const b = data[i * 4 + 2];

              // 크로마키 그린 감지 및 Alpha 투명화
              if (g - 150 > r + b) {
                data[i * 4 + 3] = 0; // 완전 투명
              } else if (g + g > r + b) {
                // 경계선 녹색 번짐(Green spill) 완화 및 부드러운 블렌딩
                const adjustment = (g - (r + b) / 2) / 3;
                data[i * 4 + 0] = r + adjustment;
                data[i * 4 + 1] = g - adjustment * 2;
                data[i * 4 + 2] = b + adjustment;
                const alpha = Math.max(0, 255 - adjustment * 4);
                data[i * 4 + 3] = alpha;
              }
            }

            mainCtx.putImageData(frame, 0, 0);
          }
        }
      }

      animFrameId = requestAnimationFrame(renderMatting);
    };

    animFrameId = requestAnimationFrame(renderMatting);
    return () => cancelAnimationFrame(animFrameId);
  }, [isWebRTCActive]);

  return (
    <section
      className="monitor monitor-avatar"
      style={{
        position: "relative",
        overflow: "hidden",
        backgroundImage: `url('${selectedBg}')`,
        backgroundSize: "cover",
        backgroundPosition: "center",
      }}
    >
      <div
        className="monitor-header"
        style={{
          position: "absolute",
          top: 12,
          left: 12,
          right: 12,
          zIndex: 10,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
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

        {/* 배경 선택 버튼 & 팝오버 메뉴 (속도 조절처럼 컴팩트) */}
        <div style={{ position: "relative" }}>
          <button
            onClick={() => setIsBgMenuOpen((prev) => !prev)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 4,
              fontSize: "0.75rem",
              background: "rgba(15, 23, 42, 0.75)",
              color: "#e2e8f0",
              border: "1px solid rgba(255, 255, 255, 0.15)",
              padding: "4px 10px",
              borderRadius: "14px",
              cursor: "pointer",
              backdropFilter: "blur(8px)",
              transition: "all 0.2s ease",
            }}
            title="아바타 배경 공간 변경"
          >
            <span>🖼️ 배경</span>
            <span style={{ opacity: 0.7, fontSize: "0.65rem" }}>▼</span>
          </button>

          {isBgMenuOpen && (
            <div
              style={{
                position: "absolute",
                top: "100%",
                right: 0,
                marginTop: 6,
                background: "rgba(23, 23, 23, 0.95)",
                border: "1px solid rgba(255, 255, 255, 0.15)",
                borderRadius: 8,
                padding: "4px",
                display: "flex",
                flexDirection: "column",
                gap: 2,
                minWidth: 120,
                zIndex: 50,
                boxShadow: "0 10px 25px rgba(0,0,0,0.6)",
                backdropFilter: "blur(12px)",
              }}
            >
              {BACKGROUND_OPTIONS.map((bg) => (
                <button
                  key={bg.id}
                  onClick={() => handleSelectBg(bg.url)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    fontSize: "0.75rem",
                    padding: "6px 10px",
                    background: selectedBg === bg.url ? "rgba(59, 130, 246, 0.25)" : "transparent",
                    color: selectedBg === bg.url ? "#60a5fa" : "#cbd5e1",
                    border: "none",
                    borderRadius: 6,
                    cursor: "pointer",
                    textAlign: "left",
                    whiteSpace: "nowrap",
                    fontWeight: selectedBg === bg.url ? 600 : 400,
                  }}
                >
                  <span>{bg.icon}</span>
                  <span>{bg.label}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 숨김 비디오 스트림 (WebRTC 오디오/비디오 수신용 - 소리 재생을 위해 muted 제거) */}
      <video
        ref={setCombinedVideoRef}
        autoPlay
        playsInline
        style={{
          position: "absolute",
          opacity: 0,
          pointerEvents: "none",
          width: "1px",
          height: "1px",
        }}
      />

      {/* 실시간 투명 매팅 캔버스 (책상 뒤 의자에 자연스럽게 위치하도록 상반신 배치 & 하반신 책상 뒤 클리핑) */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: isWebRTCActive ? "flex" : "none",
          justifyContent: "center",
          alignItems: "center",
          pointerEvents: "none",
        }}
      >
        <canvas
          ref={canvasRef}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            // 아바타의 위치를 의자 등받이 중앙에 맞추고, 책상 상판 아래(약 57% 지점 이하)를 완벽하게 가림
            transform: "translateY(-4%) scale(0.92)",
            clipPath: "polygon(0 0, 100% 0, 100% 59%, 0 59%)",
          }}
        />
      </div>

      {/* 보조 임시 캔버스 (화면에 미노출) */}
      <canvas ref={tmpCanvasRef} style={{ display: "none" }} />

      {/* 아바타 연결 전 또는 에러 시 Orb/안내문구 표시 */}
      {!isWebRTCActive && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            height: "100%",
            gap: 16,
            background: "rgba(0, 0, 0, 0.4)",
            backdropFilter: "blur(4px)",
          }}
        >
          <Orb status={status === "connecting" ? "listening" : orbState} />
          {status === "connecting" && (
            <p style={{ color: "#f1f5f9", fontSize: "0.875rem", textShadow: "0 1px 3px rgba(0,0,0,0.8)" }}>
              Azure 아바타 세션을 준비하고 있습니다...
            </p>
          )}
          {status === "error" && (
            <div style={{ textAlign: "center" }}>
              <p style={{ color: "#f87171", fontSize: "0.875rem", marginBottom: 8, textShadow: "0 1px 3px rgba(0,0,0,0.8)" }}>
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
