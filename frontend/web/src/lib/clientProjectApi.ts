const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface ClientProject {
  id: string;
  title: string;
  research_purpose: string;
  access_id?: string;
  created_at: string;
}

export interface ClientSession {
  id: string;
  /** PM이 세션 생성 시 입력한 익명 참가자 ID (PM 대시보드에 보이는 세션 제목과 동일) */
  title: string;
  status: "created" | "running" | "ended";
  duration_minutes: number;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
}

export class ClientProjectApiError extends Error {
  constructor(public readonly status: number) {
    super(`Client project request failed (${status})`);
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new ClientProjectApiError(response.status);
  }
  return response.json() as Promise<T>;
}

export async function exchangeClientProjectAccess(accessId: string): Promise<{
  project: ClientProject;
  access_token: string;
}> {
  const response = await fetch(`${API_BASE_URL}/api/client/projects/access`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ access_id: accessId.trim().toUpperCase() }),
  });
  return parseResponse(response);
}

function clientHeaders(accessToken: string): HeadersInit {
  return { "X-Project-Access-Token": accessToken };
}

export async function fetchClientProject(projectId: string, accessToken: string): Promise<ClientProject> {
  const response = await fetch(`${API_BASE_URL}/api/client/projects/${encodeURIComponent(projectId)}`, {
    headers: clientHeaders(accessToken),
  });
  return parseResponse(response);
}

export async function fetchClientProjectSessions(projectId: string, accessToken: string): Promise<ClientSession[]> {
  const response = await fetch(`${API_BASE_URL}/api/client/projects/${encodeURIComponent(projectId)}/sessions`, {
    headers: clientHeaders(accessToken),
  });
  return parseResponse(response);
}

export interface ClientTranscriptTurn {
  index: number;
  speaker: "assistant" | "interviewee";
  text: string;
  text_en: string | null;
  created_at: string;
}

export async function fetchClientTranscript(
  projectId: string,
  sessionId: string,
  accessToken: string,
): Promise<ClientTranscriptTurn[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/client/projects/${encodeURIComponent(projectId)}/sessions/${encodeURIComponent(sessionId)}/transcript`,
    { headers: clientHeaders(accessToken) },
  );
  return parseResponse(response);
}

/** 클라이언트 토큰으로 접근하는 다운로드 URL들 */
export function clientProjectReportDownloadUrl(
  projectId: string,
  format: "word" | "powerbi" | "json" = "word",
): string {
  const query = format === "word" ? "" : `?format=${encodeURIComponent(format)}`;
  return `${API_BASE_URL}/api/client/projects/${encodeURIComponent(projectId)}/aggregate-report/download${query}`;
}

export function clientTranscriptDownloadUrl(projectId: string, sessionId: string): string {
  return `${API_BASE_URL}/api/client/projects/${encodeURIComponent(projectId)}/sessions/${encodeURIComponent(sessionId)}/transcript/download`;
}

export function clientRecordingDownloadUrl(projectId: string, sessionId: string): string {
  return `${API_BASE_URL}/api/client/projects/${encodeURIComponent(projectId)}/sessions/${encodeURIComponent(sessionId)}/recording/download`;
}

export function clientDownloadHeaders(accessToken: string): HeadersInit {
  return clientHeaders(accessToken);
}
