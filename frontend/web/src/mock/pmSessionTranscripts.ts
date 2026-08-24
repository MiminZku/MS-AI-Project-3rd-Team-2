import { mockTranscript, type TranscriptTurn } from "./transcript";

const pmSessionTranscripts: Partial<Record<string, TranscriptTurn[]>> = {
  "session-01": mockTranscript,
};

export const getPmSessionTranscript = (sessionId: string): TranscriptTurn[] | undefined =>
  pmSessionTranscripts[sessionId];
