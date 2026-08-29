import { useEffect, useRef, useState } from "react";
import {
  CallClient,
  CallAgent,
  Call,
  RemoteAudioStream,
  RemoteParticipant,
  RemoteVideoStream,
  VideoStreamRenderer,
  VideoStreamRendererView,
} from "@azure/communication-calling";
import { AzureCommunicationTokenCredential } from "@azure/communication-common";

interface VideoSubscriberProps {
  token: string;
  groupId: string;
  onStreamReady?: (stream: MediaStream | null) => void;
}

export default function VideoSubscriber({ token, groupId, onStreamReady }: VideoSubscriberProps) {
  const videoContainerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    let isMounted = true;
    let callAgent: CallAgent | null = null;
    let activeCall: Call | null = null;
    let renderer: VideoStreamRenderer | null = null;
    let currentView: VideoStreamRendererView | null = null;
    let remoteVideoMediaStream: MediaStream | null = null;
    let remoteAudioMediaStream: MediaStream | null = null;

    const safeDisposeRenderer = () => {
      if (currentView) {
        try {
          currentView.dispose();
        } catch (err) {
          console.warn("VideoStreamRendererView dispose skipped:", err);
        }
        currentView = null;
      }
      if (renderer) {
        try {
          renderer.dispose();
        } catch (err) {
          console.warn("VideoStreamRenderer dispose skipped:", err);
        }
        renderer = null;
      }
      if (videoContainerRef.current) {
        videoContainerRef.current.innerHTML = "";
      }
    };

    const publishRecordingStream = () => {
      if (!isMounted) return;
      if (!remoteVideoMediaStream) {
        onStreamReady?.(null);
        return;
      }
      onStreamReady?.(
        new MediaStream([
          ...remoteVideoMediaStream.getVideoTracks(),
          ...(remoteAudioMediaStream?.getAudioTracks() ?? []),
        ]),
      );
    };

    async function subscribeToRemoteVideo(remoteVideoStream: RemoteVideoStream) {
      if (!remoteVideoStream.isAvailable || !isMounted) return;

      try {
        const stream = await remoteVideoStream.getMediaStream();
        if (!isMounted) return;
        remoteVideoMediaStream = stream;
        publishRecordingStream();

        // 기존 렌더러가 있다면 먼저 안전하게 정리
        safeDisposeRenderer();

        const newRenderer = new VideoStreamRenderer(remoteVideoStream);
        renderer = newRenderer;
        const view = await newRenderer.createView({ scalingMode: "Fit" });
        if (!isMounted) {
          try { view.dispose(); } catch {}
          try { newRenderer.dispose(); } catch {}
          return;
        }
        currentView = view;

        if (videoContainerRef.current) {
          videoContainerRef.current.innerHTML = "";
          videoContainerRef.current.appendChild(view.target);

          const videoEl = videoContainerRef.current.querySelector("video");
          if (videoEl) {
            videoEl.style.width = "100%";
            videoEl.style.height = "100%";
            videoEl.style.objectFit = "contain";
          }
        }
      } catch (err) {
        console.warn("subscribeToRemoteVideo error:", err);
      }
    }

    async function subscribeToRemoteAudio(remoteAudioStream: RemoteAudioStream) {
      if (!isMounted) return;
      try {
        remoteAudioMediaStream = await remoteAudioStream.getMediaStream();
        publishRecordingStream();
      } catch (err) {
        console.warn("subscribeToRemoteAudio error:", err);
      }
    }

    async function initAndJoinCall() {
      try {
        const callClient = new CallClient();
        const credential = new AzureCommunicationTokenCredential(token);
        const agent = await callClient.createCallAgent(credential);
        if (!isMounted) {
          try { agent.dispose(); } catch {}
          return;
        }
        callAgent = agent;

        const call = agent.join(
          { groupId },
          {
            // 참관자는 오디오와 비디오 송출을 하지 않음
            audioOptions: { muted: true },
          },
        );
        activeCall = call;

        call.remoteAudioStreams.forEach((stream) => {
          void subscribeToRemoteAudio(stream);
        });
        call.on("remoteAudioStreamsUpdated", (event) => {
          if (!isMounted) return;
          event.added.forEach((stream) => {
            void subscribeToRemoteAudio(stream);
          });
          if (event.removed.length > 0) {
            remoteAudioMediaStream = null;
            publishRecordingStream();
          }
        });

        const subscribeToParticipant = (participant: RemoteParticipant) => {
          participant.videoStreams.forEach((stream) => {
            if (stream.isAvailable) {
              void subscribeToRemoteVideo(stream);
            }
            stream.on("isAvailableChanged", () => {
              if (!isMounted) return;
              if (stream.isAvailable) {
                void subscribeToRemoteVideo(stream);
              } else {
                safeDisposeRenderer();
                remoteVideoMediaStream = null;
                publishRecordingStream();
              }
            });
          });

          participant.on("videoStreamsUpdated", (e) => {
            if (!isMounted) return;
            e.added.forEach((stream) => {
              if (stream.isAvailable) void subscribeToRemoteVideo(stream);
              stream.on("isAvailableChanged", () => {
                if (!isMounted) return;
                if (stream.isAvailable) void subscribeToRemoteVideo(stream);
                else {
                  safeDisposeRenderer();
                  remoteVideoMediaStream = null;
                  publishRecordingStream();
                }
              });
            });
            e.removed.forEach(() => {
              safeDisposeRenderer();
              remoteVideoMediaStream = null;
              publishRecordingStream();
            });
          });
        };

        // Handle already connected participants
        call.remoteParticipants.forEach(subscribeToParticipant);

        // Handle new participants joining
        call.on("remoteParticipantsUpdated", (e) => {
          if (!isMounted) return;
          e.added.forEach(subscribeToParticipant);
        });
      } catch (err: any) {
        if (!isMounted) return;
        console.error("ACS 수신 연결 실패:", err);
        setError("화상 스트림 연결에 실패했습니다.");
      }
    }

    void initAndJoinCall();

    return () => {
      isMounted = false;
      safeDisposeRenderer();
      if (activeCall) {
        try {
          void activeCall.hangUp();
        } catch (err) {
          console.warn("Call hangUp error:", err);
        }
        activeCall = null;
      }
      if (callAgent) {
        try {
          void callAgent.dispose();
        } catch (err) {
          console.warn("CallAgent dispose error:", err);
        }
        callAgent = null;
      }
      remoteVideoMediaStream = null;
      remoteAudioMediaStream = null;
      onStreamReady?.(null);
    };
  }, [token, groupId, onStreamReady]);

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        backgroundColor: "#1a1a1a",
        position: "relative",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
      }}
    >
      {error ? (
        <span style={{ color: "var(--error)", fontSize: "14px", padding: 10, textAlign: "center" }}>
          {error}
        </span>
      ) : (
        <>
          <div ref={videoContainerRef} style={{ width: "100%", height: "100%" }} />
          {!videoContainerRef.current?.hasChildNodes() && (
            <span style={{ color: "var(--muted)", position: "absolute", fontSize: 13 }}>
              화상 대기중...
            </span>
          )}
        </>
      )}
    </div>
  );
}
