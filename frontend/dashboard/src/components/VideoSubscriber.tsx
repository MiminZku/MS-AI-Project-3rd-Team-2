import { useEffect, useRef, useState } from "react";
import { CallClient, CallAgent, RemoteParticipant, RemoteVideoStream, VideoStreamRenderer } from "@azure/communication-calling";
import { AzureCommunicationTokenCredential } from "@azure/communication-common";

interface VideoSubscriberProps {
  token: string;
  groupId: string;
}

export default function VideoSubscriber({ token, groupId }: VideoSubscriberProps) {
  const videoContainerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    let callAgent: CallAgent | null = null;
    let renderer: VideoStreamRenderer | null = null;

    async function subscribeToRemoteVideo(remoteVideoStream: RemoteVideoStream) {
      if (!remoteVideoStream.isAvailable) return;
      
      renderer = new VideoStreamRenderer(remoteVideoStream);
      const view = await renderer.createView({ scalingMode: 'Crop' });
      
      if (videoContainerRef.current) {
        // Clear previous video
        videoContainerRef.current.innerHTML = '';
        videoContainerRef.current.appendChild(view.target);
        
        const videoEl = videoContainerRef.current.querySelector('video');
        if (videoEl) {
          videoEl.style.width = '100%';
          videoEl.style.height = '100%';
          videoEl.style.objectFit = 'cover';
        }
      }
    }

    async function initAndJoinCall() {
      try {
        const callClient = new CallClient();
        const credential = new AzureCommunicationTokenCredential(token);
        callAgent = await callClient.createCallAgent(credential);

        const call = callAgent.join({ groupId }, {
          // 참관자는 오디오와 비디오 송출을 하지 않음
          audioOptions: { muted: true }
        });

        const subscribeToParticipant = (participant: RemoteParticipant) => {
          participant.videoStreams.forEach(stream => {
            if (stream.isAvailable) {
              subscribeToRemoteVideo(stream);
            }
            stream.on('isAvailableChanged', () => {
              if (stream.isAvailable) {
                subscribeToRemoteVideo(stream);
              } else if (renderer) {
                renderer.dispose();
                if (videoContainerRef.current) videoContainerRef.current.innerHTML = '';
              }
            });
          });

          participant.on('videoStreamsUpdated', (e) => {
            e.added.forEach(stream => {
              if (stream.isAvailable) subscribeToRemoteVideo(stream);
              stream.on('isAvailableChanged', () => {
                if (stream.isAvailable) subscribeToRemoteVideo(stream);
              });
            });
          });
        };

        // Handle already connected participants
        call.remoteParticipants.forEach(subscribeToParticipant);

        // Handle new participants joining
        call.on('remoteParticipantsUpdated', e => {
          e.added.forEach(subscribeToParticipant);
        });

      } catch (err: any) {
        console.error("ACS 수신 연결 실패:", err);
        setError("화상 스트림 연결에 실패했습니다.");
      }
    }

    initAndJoinCall();

    return () => {
      if (renderer) renderer.dispose();
      if (callAgent) callAgent.dispose();
    };
  }, [token, groupId]);

  return (
    <div style={{
      width: "100%",
      height: "100%",
      backgroundColor: "#1a1a1a",
      position: "relative",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      overflow: "hidden"
    }}>
      {error ? (
        <span style={{ color: "var(--error)", fontSize: "14px", padding: 10, textAlign: "center" }}>{error}</span>
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
