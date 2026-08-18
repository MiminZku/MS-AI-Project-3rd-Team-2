import { useEffect, useState, useRef } from "react";

export function useAudioLevelMonitor(isActive: boolean) {
  const [isVoiceDetected, setIsVoiceDetected] = useState(false);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const animationIdRef = useRef<number | null>(null);

  // Time tracking refs
  const aboveThresholdStartTimeRef = useRef<number | null>(null);
  const belowThresholdStartTimeRef = useRef<number | null>(null);

  useEffect(() => {
    if (!isActive) {
      cleanup();
      return;
    }

    const startMonitor = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        streamRef.current = stream;

        const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
        const audioContext = new AudioContextClass();
        audioContextRef.current = audioContext;

        const source = audioContext.createMediaStreamSource(stream);
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 512;
        analyserRef.current = analyser;
        source.connect(analyser);

        const bufferLength = analyser.fftSize;
        const dataArray = new Float32Array(bufferLength);
        const threshold = 0.015; // RMS threshold

        const checkLevel = () => {
          if (!analyserRef.current) return;
          analyserRef.current.getFloatTimeDomainData(dataArray);

          // Calculate RMS (Root Mean Square)
          let sum = 0;
          for (let i = 0; i < bufferLength; i++) {
            sum += dataArray[i] * dataArray[i];
          }
          const rms = Math.sqrt(sum / bufferLength);

          const now = Date.now();

          if (rms > threshold) {
            // Start tracking duration when volume exceeds threshold
            if (aboveThresholdStartTimeRef.current === null) {
              aboveThresholdStartTimeRef.current = now;
            }
            belowThresholdStartTimeRef.current = null;

            // Trigger detection only if volume is sustained for >= 300ms
            const duration = now - aboveThresholdStartTimeRef.current;
            if (duration >= 300) {
              setIsVoiceDetected(true);
            }
          } else {
            aboveThresholdStartTimeRef.current = null;

            // Track silence duration
            if (belowThresholdStartTimeRef.current === null) {
              belowThresholdStartTimeRef.current = now;
            }

            // Sustained silence for >= 2000ms turns off detection
            const silenceDuration = now - belowThresholdStartTimeRef.current;
            if (silenceDuration >= 2000) {
              setIsVoiceDetected(false);
            }
          }

          animationIdRef.current = requestAnimationFrame(checkLevel);
        };

        animationIdRef.current = requestAnimationFrame(checkLevel);
      } catch (err) {
        console.error("Failed to initialize audio level monitor:", err);
      }
    };

    startMonitor();

    return () => cleanup();
  }, [isActive]);

  const cleanup = () => {
    if (animationIdRef.current !== null) {
      cancelAnimationFrame(animationIdRef.current);
      animationIdRef.current = null;
    }
    if (audioContextRef.current) {
      if (audioContextRef.current.state !== "closed") {
        audioContextRef.current.close();
      }
      audioContextRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    analyserRef.current = null;
    aboveThresholdStartTimeRef.current = null;
    belowThresholdStartTimeRef.current = null;
    setIsVoiceDetected(false);
  };

  return isVoiceDetected;
}
