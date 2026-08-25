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
