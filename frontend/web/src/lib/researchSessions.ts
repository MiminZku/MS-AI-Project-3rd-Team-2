import { clientResearchSessions } from "../mock/clientResearchSessions";

export type SessionStatus = "scheduled" | "completed";

export interface ClientResearchSession {
  id: string;
  projectId: string;
  participantSegment: string;
  status: SessionStatus;
  scheduledAt: string;
  completedAt?: string;
  durationMinutes: number;
  themes: string[];
  approvedQuotes: string[];
  dashboardTheme: string;
  clientVisible: boolean;
}

export interface ResearchSession extends ClientResearchSession {
  pmNote: string;
  hasTranscript: boolean;
}

export type SessionArtifact =
  | "Approved digest"
  | "Approved quotes"
  | "Themes"
  | "Full transcript"
  | "PM note"
  | "Recording"
  | "Observer controls";

export const getProjectSessions = (projectId: string): ClientResearchSession[] =>
  clientResearchSessions.filter((session) => session.projectId === projectId);

export const getResearchSession = (
  projectId: string,
  sessionId: string,
): ClientResearchSession | undefined =>
  getProjectSessions(projectId).find((session) => session.id === sessionId);

export const getPmProjectSessions = async (projectId: string): Promise<ResearchSession[]> => {
  const { pmResearchSessions } = await import("../mock/pmResearchSessions");
  return pmResearchSessions.filter((session) => session.projectId === projectId);
};

export const getPmResearchSession = async (
  projectId: string,
  sessionId: string,
): Promise<ResearchSession | undefined> => {
  const sessions = await getPmProjectSessions(projectId);
  return sessions.find((session) => session.id === sessionId);
};

export function getPermittedSessionArtifacts(
  session: Pick<ClientResearchSession, "status"> & Partial<Pick<ResearchSession, "hasTranscript">>,
  role: "pm" | "client",
): SessionArtifact[] {
  const clientArtifacts: SessionArtifact[] = [
    "Approved digest",
    "Approved quotes",
    "Themes",
  ];

  if (role === "client") return clientArtifacts;

  return session.status === "completed"
    ? [...clientArtifacts, ...(session.hasTranscript ? ["Full transcript" as const] : []), "PM note", "Recording", "Observer controls"]
    : ["Observer controls"];
}

export const getSessionRedirectPath = (
  projectId: string,
  sessionId: string,
): string | undefined =>
  getResearchSession(projectId, sessionId)
    ? undefined
    : `/projects/${projectId}/results`;
