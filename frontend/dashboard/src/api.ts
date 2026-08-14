import type { Report, Session } from "./types";

export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// WebSocket은 Static Web Apps가 아니라 백엔드(Container Apps)로 직접 연결한다 (C8).
export const WS_BASE_URL: string =
  import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000";

export const ADMIN_TOKEN: string = import.meta.env.VITE_ADMIN_TOKEN ?? "";

function headers(): HeadersInit {
  const base: Record<string, string> = { "Content-Type": "application/json" };
  if (ADMIN_TOKEN) base["X-Admin-Token"] = ADMIN_TOKEN;
  return base;
}

export interface CreateSessionInput {
  title: string;
  duration_minutes: number;
  question_script: string;
}

export interface SessionResponse {
  session: Session;
  interviewee_url: string;
}

export async function createSession(input: CreateSessionInput): Promise<SessionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/sessions`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(`세션 생성 실패 (${response.status})`);
  return response.json();
}

export async function fetchSession(sessionId: string): Promise<SessionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}`, {
    headers: headers(),
  });
  if (!response.ok) throw new Error(`세션 조회 실패 (${response.status})`);
  return response.json();
}

export async function endSession(sessionId: string): Promise<Session> {
  const response = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}/end`, {
    method: "POST",
    headers: headers(),
  });
  if (!response.ok) throw new Error(`세션 종료 실패 (${response.status})`);
  return response.json();
}

/** 리포트가 아직 생성 중이면 null (202 pending). observer 소켓의 report.ready로도 받을 수 있다. */
export async function fetchReport(sessionId: string): Promise<Report | null> {
  const response = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}/report`, {
    headers: headers(),
  });
  if (response.status === 202) return null;
  if (!response.ok) throw new Error(`리포트 조회 실패 (${response.status})`);
  return response.json();
}

export function observerSocketUrl(sessionId: string): string {
  const query = ADMIN_TOKEN ? `?token=${encodeURIComponent(ADMIN_TOKEN)}` : "";
  return `${WS_BASE_URL}/ws/observer/${sessionId}${query}`;
}
