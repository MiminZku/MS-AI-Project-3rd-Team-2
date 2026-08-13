// backend/app/schemas/messages.py 와 항상 같이 수정할 것.

export type Speaker = "interviewee" | "assistant";
export type InstructionStatus = "queued" | "applied";

export interface QuestionNode {
  id: string;
  order: number;
  text: string;
  branches: Record<string, string>;
}

export interface Session {
  id: string;
  title: string;
  status: "created" | "running" | "ended";
  duration_minutes: number;
  questions: QuestionNode[];
  current_question_index: number;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
}

export interface Turn {
  index: number;
  speaker: Speaker;
  text: string;
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
  | {
      type: "session.snapshot";
      session: Session;
      transcript: Turn[];
      instructions: Instruction[];
      interviewee_connected: boolean;
    }
  | { type: "transcript.append"; turn: Turn }
  | { type: "instruction.queued"; instruction: Instruction }
  | { type: "instruction.applied"; instruction: Instruction }
  | {
      type: "timekeeper.signal";
      should_move_on: boolean;
      remaining_minutes: number;
      remaining_questions: number;
      hint: string;
    }
  | { type: "session.ended"; session: Session }
  | { type: "report.ready"; report: Report }
  | { type: "interviewee.connected"; session_id: string }
  | { type: "interviewee.disconnected"; session_id: string }
  | { type: "error"; message: string };
