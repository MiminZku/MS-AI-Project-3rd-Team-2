// backend/app/schemas/messages.py 와 항상 같이 수정할 것.

export type Speaker = "interviewee" | "assistant";

export interface Turn {
  index: number;
  speaker: Speaker;
  text: string;
  // 인터뷰이 채널에는 절대 내려오지 않는다 (백엔드에서 제거됨).
  rationale?: string | null;
  instruction_id?: string | null;
  created_at: string;
}

export interface QuestionNode {
  id: string;
  order: number;
  text: string;
  branches?: Record<string, string>;
}

export interface SessionBrief {
  id: string;
  title: string;
  project_title?: string | null;
  status: "created" | "running" | "ended";
  duration_minutes?: number;
  /** 세션 생성 시 PM이 고른 동시통역 언어 코드 (ko | en | ja ...) */
  interpretation_language?: string;
  questions?: QuestionNode[];
}

export type ServerMessage =
  | { type: "session.state"; session: SessionBrief }
  | { type: "assistant.question"; turn: Turn }
  | { type: "error"; message: string };
