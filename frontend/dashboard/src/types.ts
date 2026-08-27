// backend/app/schemas/messages.py 와 항상 같이 수정할 것.

export type Speaker = "interviewee" | "assistant";
export type InstructionStatus = "queued" | "applied";

export interface QuestionNode {
  id: string;
  order: number;
  text: string;
  branches: Record<string, string>;
  /** 세션 생성 시 통역 언어로 미리 번역해 둔 질문 */
  text_translated?: string | null;
  branches_translated?: Record<string, string>;
}

export interface Session {
  id: string;
  study_id?: string | null;
  title: string;
  status: "created" | "running" | "ended";
  duration_minutes: number;
  interpretation_language?: string;
  questions: QuestionNode[];
  current_question_index: number;
  main_question_asked?: boolean;
  main_question_answered?: boolean;
  active_branch?: string | null;
  taken_branches?: string[];
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
}

/** backend/app/schemas/study.py ResearchStudy 와 항상 같이 수정할 것. */
export interface Project {
  id: string;
  title: string;
  access_id?: string | null;
  research_purpose: string;
  question_script: string;
  questions: QuestionNode[];
  created_at: string;
}

export interface Turn {
  index: number;
  speaker: Speaker;
  text: string;
  text_en?: string | null;
  /** AI 판단 근거 — 참관자 전용 (C5). */
  rationale: string | null;
  instruction_id: string | null;
  created_at: string;
}

export interface Instruction {
  id: string;
  session_id: string;
  text: string;
  status: InstructionStatus;
  created_at: string;
  applied_at: string | null;
  applied_turn: number | null;
}

export interface Report {
  session_id: string;
  generated_at: string;
  // 내부 구조는 리포트 담당자가 설계 중 — 확정되면 이 타입도 같이 구체화할 것.
  data: Record<string, unknown>;
}

export type ServerMessage =
  | { type: "session.state"; session: Session }
  | {
      type: "session.snapshot";
      session: Session;
      transcript: Turn[];
      instructions: Instruction[];
      interviewee_connected: boolean;
      /** pm이면 실시간 지시 가능, client면 참관 전용 */
      viewer_role?: "pm" | "client";
    }
  | { type: "transcript.append"; turn: Turn }
  | { type: "transcript.partial"; lang: "ko" | "en"; text: string }
  | { type: "transcript.final"; lang: "ko" | "en"; text: string }
  | { type: "instruction.queued"; instruction: Instruction }
  | { type: "instruction.applied"; instruction: Instruction }
  | { type: "instruction.deleted"; instruction_id: string }
  /** 책임있는 AI(공정성) 심사에서 차단되어 큐에 들어가지 않은 지시 */
  | { type: "instruction.rejected"; text: string; reason: string }
  | { type: "final_check.open"; session_id: string; window_seconds: number }
  | { type: "final_check.close"; session_id: string; reason: string }
  | {
      type: "timekeeper.signal";
      should_move_on: boolean;
      remaining_minutes: number;
      remaining_questions: number;
      hint: string;
      pace?: "ahead" | "on_track" | "behind" | "overtime";
      elapsed_minutes?: number;
      allow_probes?: boolean;
    }
  | { type: "session.started"; session: Session }
  | { type: "session.ended"; session: Session }
  | { type: "report.ready"; report: Report }
  | { type: "interviewee.connected"; session_id: string }
  | { type: "interviewee.disconnected"; session_id: string }
  | { type: "error"; message: string };
