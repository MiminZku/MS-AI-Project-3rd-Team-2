import { useCallback, useRef, useState } from "react";
import { uploadRecording } from "../config";

const PREFERRED_MIME_TYPES = ["video/webm;codecs=vp9,opus", "video/webm"];

function supportedMimeType(): string | undefined {
  return PREFERRED_MIME_TYPES.find((mimeType) => MediaRecorder.isTypeSupported(mimeType));
}

export function useLocalRecording() {
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingError, setRecordingError] = useState<string | null>(null);

  const startRecording = useCallback((stream: MediaStream) => {
    if (recorderRef.current?.state === "recording") return true;
    if (typeof MediaRecorder === "undefined") {
      setRecordingError("이 브라우저는 영상 녹화를 지원하지 않습니다.");
      return false;
    }
    if (stream.getVideoTracks().length === 0 || stream.getAudioTracks().length === 0) {
      setRecordingError("카메라 또는 마이크 권한이 준비되지 않았습니다.");
      return false;
    }

    try {
      chunksRef.current = [];
      const mimeType = supportedMimeType();
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onerror = () => setRecordingError("면접 영상 녹화 중 오류가 발생했습니다.");
      recorder.start(1000);
      recorderRef.current = recorder;
      setRecordingError(null);
      setIsRecording(true);
      return true;
    } catch (error) {
      console.error("Failed to start local recording", error);
      setRecordingError("면접 영상 녹화를 시작하지 못했습니다.");
      return false;
    }
  }, []);

  const stopAndUploadRecording = useCallback(async (sessionId: string) => {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === "inactive") return;

    const videoBlob = await new Promise<Blob>((resolve, reject) => {
      recorder.onstop = () => {
        const mimeType = recorder.mimeType || "video/webm";
        resolve(new Blob(chunksRef.current, { type: mimeType }));
      };
      recorder.onerror = () => reject(new Error("면접 영상 녹화 중 오류가 발생했습니다."));
      recorder.stop();
    });

    recorderRef.current = null;
    setIsRecording(false);
    if (videoBlob.size === 0) throw new Error("업로드할 녹화 영상이 없습니다.");

    const result = await uploadRecording(sessionId, videoBlob);
    if (result.warning) setRecordingError(result.warning);
    return result;
  }, []);

  return { isRecording, recordingError, startRecording, stopAndUploadRecording };
}
