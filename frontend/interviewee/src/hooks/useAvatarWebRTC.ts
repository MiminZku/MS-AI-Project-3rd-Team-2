import { useState, useRef, useEffect, useCallback } from "react";
import * as SpeechSDK from "microsoft-cognitiveservices-speech-sdk";

export type AvatarConnectionStatus =
  | "disconnected"
  | "connecting"
  | "connected"
  | "speaking"
  | "error";

interface UseAvatarWebRTCOptions {
  autoConnect?: boolean;
  character?: string;
  style?: string;
  voice?: string;
  transparentBackground?: boolean;
}

function encodeSSML(text: string): string {
  if (!text) return "";
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

export function useAvatarWebRTC({
  autoConnect = false,
  character = "lisa",
  style = "casual-sitting",
  voice = "en-US-AvaMultilingualNeural",
  transparentBackground = true,
}: UseAvatarWebRTCOptions = {}) {
  const [status, setStatus] = useState<AvatarConnectionStatus>("disconnected");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const peerConnectionRef = useRef<RTCPeerConnection | null>(null);
  const avatarSynthesizerRef = useRef<SpeechSDK.AvatarSynthesizer | null>(null);

  const cleanup = useCallback(() => {
    if (avatarSynthesizerRef.current) {
      try {
        avatarSynthesizerRef.current.close();
      } catch (e) {
        console.warn("Error closing avatarSynthesizer:", e);
      }
      avatarSynthesizerRef.current = null;
    }

    if (peerConnectionRef.current) {
      peerConnectionRef.current.close();
      peerConnectionRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setStatus("disconnected");
  }, []);

  const connect = useCallback(async () => {
    try {
      cleanup();
      setStatus("connecting");
      setErrorMessage(null);

      const apiKey = import.meta.env.VITE_AZURE_SPEECH_KEY;
      const region = import.meta.env.VITE_AZURE_SPEECH_REGION || "westus2";

      if (!apiKey) {
        throw new Error("VITE_AZURE_SPEECH_KEY가 frontend/interviewee/.env 에 설정되지 않았습니다.");
      }

      // 1. Azure Speech Relay Token (ICE Server) 조회
      const relayRes = await fetch(
        `https://${region}.tts.speech.microsoft.com/cognitiveservices/avatar/relay/token/v1`,
        {
          headers: {
            "Ocp-Apim-Subscription-Key": apiKey,
          },
        }
      );

      if (!relayRes.ok) {
        const errorText = await relayRes.text();
        throw new Error(`Azure Relay Token 발급 실패 (${relayRes.status}): ${errorText}`);
      }

      const relayData = await relayRes.json();
      const iceServerUrl = relayData.Urls?.[0] || relayData.urls?.[0];
      const iceServerUsername = relayData.Username || relayData.username;
      const iceServerCredential = relayData.Password || relayData.password;

      // 2. SpeechSDK Config & AvatarConfig 구성
      const speechSynthesisConfig = SpeechSDK.SpeechConfig.fromSubscription(apiKey, region);
      const videoFormat = new SpeechSDK.AvatarVideoFormat();
      videoFormat.setCropRange(new SpeechSDK.Coordinate(0, 0), new SpeechSDK.Coordinate(1920, 1080));

      const avatarConfig = new SpeechSDK.AvatarConfig(character, style, videoFormat);
      avatarConfig.customized = false;
      // 투명 배경 매팅을 위해 크로마키 그린(#00FF00FF) 설정
      avatarConfig.backgroundColor = transparentBackground ? "#00FF00FF" : "#1d1d1fFF";
      if (iceServerUrl) {
        avatarConfig.remoteIceServers = [
          {
            urls: [iceServerUrl],
            username: iceServerUsername,
            credential: iceServerCredential,
          },
        ];
      }

      // 3. RTCPeerConnection 생성
      const pc = new RTCPeerConnection({
        iceServers: iceServerUrl
          ? [
              {
                urls: [iceServerUrl],
                username: iceServerUsername,
                credential: iceServerCredential,
              },
            ]
          : [{ urls: ["stun:stun.l.google.com:19302"] }],
      });
      peerConnectionRef.current = pc;

      const remoteStream = new MediaStream();

      pc.ontrack = (event) => {
        if (event.track) {
          remoteStream.addTrack(event.track);
          if (videoRef.current) {
            videoRef.current.srcObject = remoteStream;
            videoRef.current.play().catch((err) => {
              console.warn("Avatar video autoplay:", err);
            });
          }
        }
      };

      pc.oniceconnectionstatechange = () => {
        console.log("Avatar WebRTC state:", pc.iceConnectionState);
        if (pc.iceConnectionState === "connected" || pc.iceConnectionState === "completed") {
          setStatus("connected");
        } else if (
          pc.iceConnectionState === "failed" ||
          pc.iceConnectionState === "disconnected"
        ) {
          setStatus("error");
          setErrorMessage(`WebRTC 연결 실패 (${pc.iceConnectionState})`);
        }
      };

      // 4. DataChannel 생성 및 송수신 트랜시버 등록
      pc.createDataChannel("eventChannel");
      pc.addTransceiver("video", { direction: "sendrecv" });
      pc.addTransceiver("audio", { direction: "sendrecv" });

      // 5. SpeechSDK AvatarSynthesizer 생성 및 WebRTC 시작
      const synthesizer = new SpeechSDK.AvatarSynthesizer(speechSynthesisConfig, avatarConfig);
      avatarSynthesizerRef.current = synthesizer;

      synthesizer.avatarEventReceived = (_s: any, e: any) => {
        console.log("Avatar event:", e.description);
      };

      const result = await synthesizer.startAvatarAsync(pc);
      if (result.reason === SpeechSDK.ResultReason.SynthesizingAudioCompleted) {
        console.log("Avatar session successfully started!");
        setStatus("connected");
      } else {
        if (result.reason === SpeechSDK.ResultReason.Canceled) {
          const cancellation = SpeechSDK.CancellationDetails.fromResult(result as any);
          throw new Error(`아바타 시작 취소: ${cancellation.errorDetails || cancellation.reason}`);
        }
        setStatus("connected");
      }
    } catch (err: any) {
      console.error("Avatar connection error:", err);
      setStatus("error");
      setErrorMessage(err.message || "아바타 연결 중 오류가 발생했습니다.");
    }
  }, [character, style, voice, transparentBackground, cleanup]);

  const speak = useCallback(
    async (text: string, customVoice?: string, speedRate: number = 1.1) => {
      const synthesizer = avatarSynthesizerRef.current;
      if (!synthesizer) {
        console.warn("Avatar synthesizer is not ready yet.");
        return;
      }

      try {
        setStatus("speaking");
        if (videoRef.current) {
          videoRef.current.muted = false;
          videoRef.current.volume = 1.0;
          videoRef.current.play().catch(() => {});
        }
        const activeVoice = customVoice || voice;
        // speedRate(예: 0.8, 1.0, 1.2, 1.4, 1.6) -> SSML rate 퍼센티지 변환
        const ratePercent = Math.round((speedRate - 1) * 100);
        const rateStr = ratePercent >= 0 ? `+${ratePercent}%` : `${ratePercent}%`;

        const cleanText = encodeSSML(text);
        const spokenSsml = `<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='http://www.w3.org/2001/mstts' xml:lang='en-US'><voice name='${activeVoice}'><mstts:leadingsilence-exact value='0'/><prosody rate='${rateStr}'>${cleanText}</prosody></voice></speak>`;

        console.log(`Avatar speak start (${speedRate}x, rate=${rateStr}):`, text);
        
        // 15초 타임아웃 가드: SSML 합성이 무한 대기에 빠져 아바타 상태가 speaking에 멈추는 것 방지
        const speakPromise = synthesizer.speakSsmlAsync(spokenSsml);
        const timeoutPromise = new Promise<any>((resolve) =>
          setTimeout(() => resolve({ reason: "timeout" }), 15000)
        );

        const result = await Promise.race([speakPromise, timeoutPromise]);
        if (result && result.reason === SpeechSDK.ResultReason.SynthesizingAudioCompleted) {
          console.log("Avatar speak completed.");
        } else if (result && result.reason === "timeout") {
          console.warn("Avatar speak timed out after 15s - recovering status to connected.");
        } else if (result && result.reason === SpeechSDK.ResultReason.Canceled) {
          const cancellation = SpeechSDK.CancellationDetails.fromResult(result as any);
          console.error("Avatar speak canceled:", cancellation.reason, cancellation.errorDetails);
        } else {
          console.warn("Avatar speak result reason:", result?.reason);
        }
        setStatus("connected");
      } catch (err: any) {
        console.error("Avatar speak error:", err);
        setStatus("connected");
      }
    },
    [voice]
  );

  useEffect(() => {
    if (autoConnect) {
      connect();
    }
    return () => {
      cleanup();
    };
  }, [autoConnect, connect, cleanup]);

  const stopSpeaking = useCallback(async () => {
    try {
      setStatus("connected");
      // videoRef.current.muted 강제 변경 및 speakTextAsync(' ')를 배제하여
      // 브라우저 오디오 정책 차단 및 아바타 합성기 상태 오염을 방지
    } catch (e) {
      console.warn("Error stopping avatar speaking:", e);
    }
  }, []);

  return {
    videoRef,
    status,
    errorMessage,
    connect,
    speak,
    stopSpeaking,
    disconnect: cleanup,
  };
}
