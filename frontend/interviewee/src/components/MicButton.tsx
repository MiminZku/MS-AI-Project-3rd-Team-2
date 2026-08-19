import { useState, useRef } from "react";

interface MicButtonProps {
  isRecording: boolean;
  onRecordingChange: (isRecording: boolean) => void;
  onRecordingComplete?: (blob: Blob) => void;
}

export default function MicButton({ isRecording, onRecordingChange, onRecordingComplete }: MicButtonProps) {
  const [errorMsg, setErrorMsg] = useState("");
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = async () => {
    setErrorMsg("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(chunksRef.current, { type: "audio/webm" });
        const audioUrl = URL.createObjectURL(audioBlob);
        console.log("Local recording finished. Audio Blob URL:", audioUrl);
        console.log("Audio Blob size:", audioBlob.size, "bytes");
        if (onRecordingComplete) {
          onRecordingComplete(audioBlob);
        }
      };

      mediaRecorder.start();
      onRecordingChange(true);
    } catch (err: any) {
      console.error("Failed to start recording:", err);
      setErrorMsg("마이크 권한을 허용해야 녹음이 가능합니다.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
    }
    onRecordingChange(false);
  };

  const handleMicClick = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  return (
    <section className="mic-button-panel">
      <div className={`mic-wrapper ${isRecording ? "recording" : "idle"}`} onClick={handleMicClick}>
        <div className="mic-glow" />
        <div className="mic-wave wave-1" />
        <div className="mic-wave wave-2" />
        <button className="mic-core" aria-label="Toggle Microphone">
          🎤
        </button>
      </div>
      <p className="mic-status-text">
        {isRecording ? "녹음 중... (다시 누르면 정지)" : "누르면 답변 녹음 시작"}
      </p>
      {errorMsg && <p className="error-alert" style={{ marginTop: 12, width: "100%", textAlign: "center" }}>{errorMsg}</p>}
    </section>
  );
}
