import type { Instruction, Report, Session, Turn } from "./types";

/** 백엔드 없이 관리자 대시보드 레이아웃을 리뷰하기 위한 고정 목데이터. */
export const DEMO_SESSION_ID = "demo";

export const DEMO_SESSION: Session = {
  id: DEMO_SESSION_ID,
  title: "배달 서비스 이용 경험 / P-017",
  status: "running",
  duration_minutes: 60,
  questions: [
    { id: "q1", order: 1, text: "배달 앱을 주로 어떤 상황에서 사용하시나요?", branches: {} },
    {
      id: "q2",
      order: 2,
      text: "배달비 때문에 주문을 망설인 적이 있나요?",
      branches: {
        있다: "얼마 정도의 배달비부터 부담을 느끼시나요?",
        없다: "배달비가 올라도 계속 쓰게 되는 이유가 있나요?",
      },
    },
    {
      id: "q3",
      order: 3,
      text: "최소주문금액에 대해 어떻게 느끼시나요?",
      branches: {
        부담됨: "그 때문에 주문을 포기한 경험이 있나요?",
        보통: "최소주문금액을 맞추려고 더 시킨 적은 있나요?",
      },
    },
    { id: "q4", order: 4, text: "경쟁 앱과 비교했을 때 차이를 느끼나요?", branches: {} },
  ],
  current_question_index: 2,
  created_at: new Date(Date.now() - 20 * 60_000).toISOString(),
  started_at: new Date(Date.now() - 14 * 60_000).toISOString(),
  ended_at: null,
};

export const DEMO_TRANSCRIPT: Turn[] = [
  {
    index: 0,
    speaker: "assistant",
    text: "배달비 때문에 주문을 망설인 적이 있으신가요?",
    rationale: null,
    instruction_id: null,
    created_at: new Date(Date.now() - 10 * 60_000).toISOString(),
  },
  {
    index: 1,
    speaker: "interviewee",
    text: "네, 요즘엔 배달비가 너무 올라서요. 3천 원 넘어가면 그냥 안 시켜요.",
    rationale: null,
    instruction_id: null,
    created_at: new Date(Date.now() - 9 * 60_000).toISOString(),
  },
  {
    index: 2,
    speaker: "assistant",
    text: "최소주문금액에 대해서는 어떻게 느끼시나요?",
    rationale:
      '응답자가 "망설인 적 있다"로 답해 [있다] 분기 진입. "3천 원"이라는 구체적 기준이 나와, 부담 임계 금액을 더 확인하는 파생질문으로 이어감.',
    instruction_id: null,
    created_at: new Date(Date.now() - 8 * 60_000).toISOString(),
  },
  {
    index: 3,
    speaker: "interviewee",
    text: "사실 그것도 부담이에요. 최소주문금액 맞추려고 굳이 더 시킨 적도 많고…",
    rationale: null,
    instruction_id: null,
    created_at: new Date(Date.now() - 7 * 60_000).toISOString(),
  },
];

export const DEMO_INSTRUCTIONS: Instruction[] = [
  {
    id: "ins1",
    session_id: DEMO_SESSION_ID,
    text: "어떤 상황에서 앱을 쓰는지 먼저 물어봐 주세요.",
    status: "applied",
    created_at: new Date(Date.now() - 13 * 60_000).toISOString(),
    applied_at: new Date(Date.now() - 12 * 60_000).toISOString(),
    applied_turn: 0,
  },
  {
    id: "ins2",
    session_id: DEMO_SESSION_ID,
    text: "배달비 부담을 느낀 구체적 기준 금액을 물어봐 주세요.",
    status: "applied",
    created_at: new Date(Date.now() - 9 * 60_000).toISOString(),
    applied_at: new Date(Date.now() - 8 * 60_000).toISOString(),
    applied_turn: 2,
  },
];

export const DEMO_REPORT: Report = {
  session_id: DEMO_SESSION_ID,
  generated_at: new Date().toISOString(),
  data: {
    summary:
      "배달비와 최소주문금액 모두 3천 원대에서 체감 부담이 시작됨. 두 조건 모두에서 주문 포기/추가주문 행동이 관찰됨.",
  },
};
