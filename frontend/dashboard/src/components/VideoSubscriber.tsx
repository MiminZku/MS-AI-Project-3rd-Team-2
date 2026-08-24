import { useEffect, useRef, useState } from "react";
import { CallClient, CallAgent, RemoteAudioStream, RemoteParticipant, RemoteVideoStream, VideoStreamRenderer } from "@azure/communication-calling";
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
    let callAgent: CallAgent | null = null;
    let renderer: VideoStreamRenderer | null = null;
    let remoteVideoMediaStream: MediaStream | null = null;
    let remoteAudioMediaStream: MediaStream | null = null;

    const publishRecordingStream = () => {
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
      if (!remoteVideoStream.isAvailable) return;

      remoteVideoMediaStream = await remoteVideoStream.getMediaStream();
      publishRecordingStream();
      
      renderer = new VideoStreamRenderer(remoteVideoStream);
      const view = await renderer.createView({ scalingMode: 'Fit' });
      
      if (videoContainerRef.current) {
        // Clear previous video
        videoContainerRef.current.innerHTML = '';
        videoContainerRef.current.appendChild(view.target);
        
        const videoEl = videoContainerRef.current.querySelector('video');
        if (videoEl) {
          videoEl.style.width = '100%';
          videoEl.style.height = '100%';
          videoEl.style.objectFit = 'contain';
        }
      }
    }

    async function subscribeToRemoteAudio(remoteAudioStream: RemoteAudioStream) {
      remoteAudioMediaStream = await remoteAudioStream.getMediaStream();
      publishRecordingStream();
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

        call.remoteAudioStreams.forEach(stream => {
          void subscribeToRemoteAudio(stream);
        });
        call.on("remoteAudioStreamsUpdated", event => {
          event.added.forEach(stream => {
            void subscribeToRemoteAudio(stream);
          });
          if (event.removed.length > 0) {
            remoteAudioMediaStream = null;
            publishRecordingStream();
          }
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
                remoteVideoMediaStream = null;
                publishRecordingStream();
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
      remoteVideoMediaStream = null;
      remoteAudioMediaStream = null;
      onStreamReady?.(null);
    };
  }, [token, groupId, onStreamReady]);

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
