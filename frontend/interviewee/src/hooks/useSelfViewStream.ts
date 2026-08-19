import { useEffect, useRef, useState } from "react";

/** 응답자 모니터(셀프뷰)용 카메라 스트림.
 * 오디오는 MicButton / useAudioLevelMonitor 가 따로 다루므로 video 만 잡는다. */
export function useSelfViewStream(isActive: boolean) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [isCameraOn, setIsCameraOn] = useState(false);

  useEffect(() => {
    let isCancelled = false;

    const stop = () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
      setIsCameraOn(false);
    };

    if (!isActive) {
      stop();
      return;
    }

    const start = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "user" },
          audio: false,
        });
        if (isCancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        setIsCameraOn(true);
      } catch (err) {
        console.error("Self view camera failed:", err);
        setIsCameraOn(false);
      }
    };

    start();

    return () => {
      isCancelled = true;
      stop();
    };
  }, [isActive]);

  return { videoRef, isCameraOn };
}
