/**
 * 다운로드 센터가 쓰는 백엔드 API (PM 경로).
 *
 * 클라이언트 경로는 Project Access 토큰을 쓰는 clientProjectApi.ts 를 사용한다.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const ADMIN_TOKEN = import.meta.env.VITE_ADMIN_TOKEN ?? "";

export interface ResearchProjectSummary {
  id: string;
  title: string;
  research_purpose: string;
  access_id?: string;
  created_at: string;
}

export interface ResearchSessionSummary {
  id: string;
  title: string;
  status: "created" | "running" | "ended";
  duration_minutes: number;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
  video_recording_url: string | null;
}

export type ProjectReportStatus = "NOT_GENERATED" | "GENERATING" | "COMPLETED" | "FAILED";

export interface ProjectAggregateReport {
  project_id: string;
  status: ProjectReportStatus;
  generated_at: string | null;
  included_session_ids: string[];
  respondent_count: number;
  error_message: string | null;
}

export class ResearchApiError extends Error {
  constructor(
    public readonly status: number,
    message?: string,
  ) {
    super(message ?? `요청이 실패했습니다 (${status})`);
  }
}

function headers(): HeadersInit {
  return ADMIN_TOKEN ? { "X-Admin-Token": ADMIN_TOKEN } : {};
}

async function parse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail: string | undefined;
    try {
      detail = (await response.json())?.detail;
    } catch {
      detail = undefined;
    }
    throw new ResearchApiError(response.status, detail);
  }
  return response.json() as Promise<T>;
}

export async function fetchProjects(): Promise<ResearchProjectSummary[]> {
  const response = await fetch(`${API_BASE_URL}/api/projects`, { headers: headers() });
  return parse(response);
}

export async function fetchProjectSessions(projectId: string): Promise<ResearchSessionSummary[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/projects/${encodeURIComponent(projectId)}/sessions`,
    { headers: headers() },
  );
  return parse(response);
}

export async function fetchProjectReport(projectId: string): Promise<ProjectAggregateReport> {
  const response = await fetch(
    `${API_BASE_URL}/api/projects/${encodeURIComponent(projectId)}/aggregate-report`,
    { headers: headers() },
  );
  return parse(response);
}

export async function generateProjectReport(projectId: string): Promise<ProjectAggregateReport> {
  const response = await fetch(
    `${API_BASE_URL}/api/projects/${encodeURIComponent(projectId)}/aggregate-report`,
    { method: "POST", headers: headers() },
  );
  return parse(response);
}

/**
 * 브라우저에서 파일을 내려받는다.
 *
 * 인증 헤더가 필요할 수 있어 단순 링크 대신 fetch -> Blob -> 임시 앵커 방식을 쓴다.
 * 서버가 보낸 Content-Disposition 파일명을 최대한 살린다.
 */
export async function downloadFile(url: string, requestHeaders: HeadersInit = {}): Promise<void> {
  const response = await fetch(url, { headers: requestHeaders });
  if (!response.ok) {
    let detail: string | undefined;
    try {
      detail = (await response.json())?.detail;
    } catch {
      detail = undefined;
    }
    throw new ResearchApiError(response.status, detail);
  }

  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filenameFromResponse(response) ?? "download";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}

function filenameFromResponse(response: Response): string | null {
  const disposition = response.headers.get("Content-Disposition");
  if (!disposition) return null;

  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch {
      /* 인코딩이 깨졌으면 아래 ASCII 파일명으로 폴백 */
    }
  }

  const asciiMatch = disposition.match(/filename="([^"]+)"/i);
  return asciiMatch ? asciiMatch[1] : null;
}

export function projectReportDownloadUrl(projectId: string): string {
  return `${API_BASE_URL}/api/projects/${encodeURIComponent(projectId)}/aggregate-report/download`;
}

export function transcriptDownloadUrl(sessionId: string): string {
  return `${API_BASE_URL}/api/sessions/${encodeURIComponent(sessionId)}/transcript/download`;
}

export function recordingDownloadUrl(sessionId: string): string {
  return `${API_BASE_URL}/api/sessions/${encodeURIComponent(sessionId)}/recording/download`;
}

export function adminHeaders(): HeadersInit {
  return headers();
}
