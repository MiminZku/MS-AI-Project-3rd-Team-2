export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// WebSocket은 Static Web Apps가 아니라 백엔드(Container Apps)로 직접 연결한다 (C8).
export const WS_BASE_URL: string =
  import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000";

/** 응답자는 대시보드가 발급한 ?session=... 링크로 들어온다. 
 * 로컬 개발 편의를 위해 파라미터가 없는 경우 'default-session'으로 폴백한다. */
export function sessionIdFromUrl(): string {
  const urlSession = new URLSearchParams(window.location.search).get("session");
  if (urlSession) {
    localStorage.setItem("interview_session_id", urlSession);
    return urlSession;
  }
  return localStorage.getItem("interview_session_id") ?? "default-session";
}

export async function fetchRtcToken(sessionId: string): Promise<{ user_id: string; token: string; group_id: string }> {
  const response = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}/rtc/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role: "interviewee" }),
  });
  if (!response.ok) {
    throw new Error(`ACS 토큰 발급 실패 (${response.status})`);
  }
  return response.json();
}
