export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// WebSocket은 Static Web Apps가 아니라 백엔드(Container Apps)로 직접 연결한다 (C8).
export const WS_BASE_URL: string =
  import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000";

/** 응답자는 대시보드가 발급한 ?session=... 링크로 들어온다. */
export function sessionIdFromUrl(): string {
  return new URLSearchParams(window.location.search).get("session") ?? "";
}
