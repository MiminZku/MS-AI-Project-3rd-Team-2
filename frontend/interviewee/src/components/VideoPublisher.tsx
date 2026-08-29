import { useEffect } from "react";
import { CallClient, CallAgent, LocalVideoStream } from "@azure/communication-calling";
import { AzureCommunicationTokenCredential } from "@azure/communication-common";

interface VideoPublisherProps {
  token: string;
  groupId: string;
}

export default function VideoPublisher({ token, groupId }: VideoPublisherProps) {
  useEffect(() => {
    let callAgent: CallAgent | null = null;

    async function initAndJoinCall() {
      try {
        const callClient = new CallClient();
        const credential = new AzureCommunicationTokenCredential(token);
        callAgent = await callClient.createCallAgent(credential);
        
        const deviceManager = await callClient.getDeviceManager();
        await deviceManager.askDevicePermission({ video: true, audio: true });
        
        const cameras = await deviceManager.getCameras();
        let localVideoStream: LocalVideoStream | undefined;

        if (cameras.length > 0) {
          // Use the first available camera for publishing
          const camera = cameras[0];
          localVideoStream = new LocalVideoStream(camera);
        }

        // Join the group call using the session ID as the Group ID
        await callAgent.join({ groupId }, {
          videoOptions: localVideoStream ? { localVideoStreams: [localVideoStream] } : undefined,
          // We can leave audio unmuted if we want to stream microphone.
          audioOptions: { muted: false }
        });

      } catch (err: any) {
        console.error("ACS 화상 스트림 퍼블리시 실패:", err);
      }
    }

    initAndJoinCall();

    return () => {
      if (callAgent) {
        try {
          callAgent.dispose();
        } catch (e) {
          console.warn("Error disposing callAgent in VideoPublisher:", e);
        }
      }
    };
  }, [token, groupId]);

  // UI 렌더링 없음 (백그라운드에서 송출만 담당)
  return null;
}
