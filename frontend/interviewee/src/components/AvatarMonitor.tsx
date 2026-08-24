import { useEffect, useRef, useState } from "react";
import Orb from "./Orb";
import { AvatarConnectionStatus } from "../hooks/useAvatarWebRTC";

interface AvatarMonitorProps {
  videoRef?: React.Ref<HTMLVideoElement>;
  status?: AvatarConnectionStatus;
  orbState?: "idle" | "speaking" | "listening";
  errorMessage?: string | null;
  onRetry?: () => void;
  speechSpeed?: number;
  onSpeedChange?: (speed: number) => void;
}

const SPEED_OPTIONS = [
  { value: 1.0, label: "1.0x (보통)" },
  { value: 1.25, label: "1.25x (기본 · 추천)" },
  { value: 1.5, label: "1.5x (조금 빠름)" },
  { value: 1.75, label: "1.75x (매우 빠름)" },
];

const BACKGROUND_OPTIONS = [
  { id: "bg2", label: "모던 화이트", icon: "🏛️", url: "/bg2.jpg" },
  { id: "bg5", label: "코지 룸", icon: "☕", url: "/bg5.jpg" },
];

export default function AvatarMonitor({
  videoRef,
  status = "connected",
  orbState = "idle",
  errorMessage,
  onRetry,
  speechSpeed = 1.25,
  onSpeedChange,
}: AvatarMonitorProps) {
  const isWebRTCActive = status === "connected" || status === "speaking";
  const [selectedBg, setSelectedBg] = useState<string>(() => {
    const saved = localStorage.getItem("gromit_avatar_bg");
    if (saved === "/bg2.jpg" || saved === "/bg5.jpg") {
      return saved;
    }
    return "/bg2.jpg";
  });
  const [isBgMenuOpen, setIsBgMenuOpen] = useState(false);
  const [isSpeedMenuOpen, setIsSpeedMenuOpen] = useState(false);

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
      {/* 상단 라벨 & 상태 인디케이터 (겹침 0% 유동형 뱃지 바) */}
      <div className="monitor-top-bar">
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", pointerEvents: "auto" }}>
          <span className="monitor-tag">AI 모더레이터</span>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "5px",
              background: "rgba(239, 68, 68, 0.2)",
              border: "1px solid rgba(239, 68, 68, 0.45)",
              color: "#fca5a5",
              fontSize: "0.72rem",
              fontWeight: 700,
              padding: "4px 8px",
              borderRadius: "12px",
              backdropFilter: "blur(6px)",
              letterSpacing: "0.5px",
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: "#ef4444",
                boxShadow: "0 0 8px #ef4444",
              }}
            />
            LIVE
          </span>
          {status === "connecting" && (
            <span style={{ fontSize: "0.75rem", background: "rgba(0,0,0,0.6)", color: "#60a5fa", padding: "4px 8px", borderRadius: 12, border: "1px solid rgba(96,165,250,0.3)" }}>
              아바타 연결 중...
            </span>
          )}
          {status === "speaking" && (
            <span style={{ fontSize: "0.75rem", background: "rgba(34,197,94,0.85)", color: "#fff", padding: "4px 10px", borderRadius: 12, fontWeight: 600, boxShadow: "0 2px 8px rgba(34,197,94,0.3)" }}>
              말하는 중 🎙️
            </span>
          )}
          {status === "error" && (
            <span style={{ fontSize: "0.75rem", background: "rgba(239,68,68,0.85)", color: "#fff", padding: "4px 10px", borderRadius: 12 }}>
              연결 오류
            </span>
          )}
        </div>
      </div>

      {/* 하단 중앙 컨트롤러 바 (속도 조절 + 배경 선택) */}
      <div
        style={{
          position: "absolute",
          bottom: 12,
          left: "50%",
          transform: "translateX(-50%)",
          zIndex: 20,
          display: "flex",
          alignItems: "center",
          gap: 8,
          background: "rgba(15, 23, 42, 0.7)",
          padding: "4px 8px",
          borderRadius: "20px",
          border: "1px solid rgba(255, 255, 255, 0.15)",
          backdropFilter: "blur(10px)",
          boxShadow: "0 4px 14px rgba(0, 0, 0, 0.35)",
        }}
      >
        {/* 음성 속도 조절 버튼 & 팝오버 (위로 팝업) */}
        {onSpeedChange && (
          <div style={{ position: "relative" }}>
            <button
              onClick={() => {
                setIsSpeedMenuOpen((prev) => !prev);
                setIsBgMenuOpen(false);
              }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 4,
                fontSize: "0.75rem",
                background: "rgba(15, 23, 42, 0.8)",
                color: "#93c5fd",
                border: "1px solid rgba(96, 165, 250, 0.35)",
                padding: "5px 10px",
                borderRadius: "14px",
                cursor: "pointer",
                backdropFilter: "blur(8px)",
                transition: "all 0.2s ease",
                boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
              }}
              title="아바타 발화 속도 조절"
            >
              <span>⚡ {speechSpeed}x</span>
              <span style={{ opacity: 0.7, fontSize: "0.65rem" }}>▲</span>
            </button>

            {isSpeedMenuOpen && (
              <div
                style={{
                  position: "absolute",
                  bottom: "100%",
                  right: 0,
                  marginBottom: 6,
                  background: "rgba(23, 23, 23, 0.95)",
                  border: "1px solid rgba(255, 255, 255, 0.15)",
                  borderRadius: 8,
                  padding: "4px",
                  display: "flex",
                  flexDirection: "column",
                  gap: 2,
                  minWidth: 130,
                  zIndex: 50,
                  boxShadow: "0 10px 25px rgba(0,0,0,0.6)",
                  backdropFilter: "blur(12px)",
                }}
              >
                {SPEED_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => {
                      onSpeedChange(opt.value);
                      setIsSpeedMenuOpen(false);
                    }}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      fontSize: "0.75rem",
                      padding: "6px 10px",
                      background: speechSpeed === opt.value ? "rgba(59, 130, 246, 0.25)" : "transparent",
                      color: speechSpeed === opt.value ? "#60a5fa" : "#cbd5e1",
                      border: "none",
                      borderRadius: 6,
                      cursor: "pointer",
                      textAlign: "left",
                      whiteSpace: "nowrap",
                      fontWeight: speechSpeed === opt.value ? 600 : 400,
                    }}
                  >
                    <span>{opt.label}</span>
                    {speechSpeed === opt.value && <span>✓</span>}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 배경 선택 버튼 & 팝오버 메뉴 (위로 팝업) */}
        <div style={{ position: "relative" }}>
          <button
            onClick={() => {
              setIsBgMenuOpen((prev) => !prev);
              setIsSpeedMenuOpen(false);
            }}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 4,
              fontSize: "0.75rem",
              background: "rgba(15, 23, 42, 0.8)",
              color: "#e2e8f0",
              border: "1px solid rgba(255, 255, 255, 0.2)",
              padding: "5px 10px",
              borderRadius: "14px",
              cursor: "pointer",
              backdropFilter: "blur(8px)",
              transition: "all 0.2s ease",
              boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
            }}
            title="아바타 배경 공간 변경"
          >
            <span>🖼️ 배경</span>
            <span style={{ opacity: 0.7, fontSize: "0.65rem" }}>▲</span>
          </button>

          {isBgMenuOpen && (
            <div
              style={{
                position: "absolute",
                bottom: "100%",
                right: 0,
                marginBottom: 6,
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

      {/* 실시간 투명 매팅 캔버스 (피부 선명도 100% 보존 + 책상 밑 1% 초정밀 페더링 마스크) */}
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
            // 배경별 최적 비율: 코지룸은 의자 등받이에 딱 맞추고, 모던화이트는 책상과 자연스럽게 매칭
            transform: selectedBg === "/bg5.jpg" ? "translateY(0.5%) scale(1.01)" : "translateY(-2.5%) scale(0.95)",
            // 상반신/팔 텍스처는 100% 완전 불투명(선명도 완벽 보존) & 책상 상판 밑 1%에서만 부드럽게 마스킹
            maskImage: "linear-gradient(to bottom, black 0%, black 58.5%, rgba(0,0,0,0.5) 59.3%, transparent 60%)",
            WebkitMaskImage: "linear-gradient(to bottom, black 0%, black 58.5%, rgba(0,0,0,0.5) 59.3%, transparent 60%)",
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
