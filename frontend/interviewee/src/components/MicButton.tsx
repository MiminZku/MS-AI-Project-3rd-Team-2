import { useState, useRef } from "react";

interface MicButtonProps {
  isRecording: boolean;
  onRecordingChange: (isRecording: boolean) => void;
  onAudioChunk?: (base64PCM: string) => void;
  onRecordingStart?: () => void;
  onRecordingStop?: () => void;
}

// Helper to convert Float32Array to 16-bit PCM buffer
function floatTo16BitPCM(input: Float32Array): Int16Array {
  const output = new Int16Array(input.length);
  for (let i = 0; i < input.length; i++) {
    const s = Math.max(-1, Math.min(1, input[i]));
    output[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
  }
  return output;
}

// Helper to encode Int16Array to Base64
function bufferToBase64(buffer: Int16Array): string {
  const uint8 = new Uint8Array(buffer.buffer);
  let binary = "";
  for (let i = 0; i < uint8.byteLength; i++) {
    binary += String.fromCharCode(uint8[i]);
  }
  return window.btoa(binary);
}

export default function MicButton({ isRecording, onRecordingChange, onAudioChunk, onRecordingStart, onRecordingStop }: MicButtonProps) {
  const [errorMsg, setErrorMsg] = useState("");
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);

  const startRecording = async () => {
    setErrorMsg("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 24000,
        },
      });
      streamRef.current = stream;

      // Realtime API defaults to 24kHz.
      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 });
      audioContextRef.current = audioCtx;

      const source = audioCtx.createMediaStreamSource(stream);
      sourceRef.current = source;

      // 4096 frames = ~170ms at 24kHz
      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        const pcm16 = floatTo16BitPCM(inputData);
        const base64Chunk = bufferToBase64(pcm16);
        if (onAudioChunk) {
          onAudioChunk(base64Chunk);
        }
      };

      source.connect(processor);
      processor.connect(audioCtx.destination);

      if (onRecordingStart) onRecordingStart();
      onRecordingChange(true);
    } catch (err: any) {
      console.error("Failed to start recording:", err);
      setErrorMsg("마이크 권한을 허용해야 녹음이 가능합니다.");
    }
  };

  const stopRecording = () => {
    if (processorRef.current && sourceRef.current) {
      sourceRef.current.disconnect();
      processorRef.current.disconnect();
    }
    if (audioContextRef.current && audioContextRef.current.state !== "closed") {
      audioContextRef.current.close();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
    }
    if (onRecordingStop) onRecordingStop();
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
