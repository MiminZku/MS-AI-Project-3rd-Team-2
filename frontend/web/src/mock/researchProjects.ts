export type ProjectStatus = "ready" | "processing";
export type DashboardMode = "evidence" | "coverage" | "session";

export interface EvidenceItem {
  theme: string;
  count: number;
  summary: string;
}

export interface FocusedEvidence {
  theme: string;
  summary: string;
  quote: string;
  sessionCount: number;
  nextAction: string;
}

export interface ResearchProject {
  id: string;
  title: string;
  subtitle: string;
  description: string;
  status: ProjectStatus;
  updatedAt: string;
  owner: string;
  sessions: {
    completed: number;
    total: number;
  };
  coverageScore: number;
  evidenceCount: number;
  keyFindingCount: number;
  researchGaps: number;
  evidence: EvidenceItem[];
  coverage: EvidenceItem[];
  sessionStatus: EvidenceItem[];
  focusedEvidence?: Partial<Record<DashboardMode, FocusedEvidence[]>>;
  sessionThemeMap?: Record<string, string>;
  highlights: string[];
}

export const researchProjects: ResearchProject[] = [
  {
    id: "workflow-discovery",
    title: "업무 워크플로우 탐색 조사",
    subtitle: "내부 운영자의 반복 업무와 개선 기회를 찾습니다.",
    description: "업무 시작부터 예외 처리까지의 흐름을 관찰하고, 자동화 우선순위를 정리한 탐색형 인터뷰입니다.",
    status: "ready",
    updatedAt: "2026. 08. 20.",
    owner: "Research Operations",
    sessions: { completed: 18, total: 20 },
    coverageScore: 86,
    evidenceCount: 47,
    keyFindingCount: 6,
    researchGaps: 2,
    evidence: [
      { theme: "반복 입력", count: 15, summary: "같은 고객·주문 정보를 여러 시스템에 다시 입력합니다." },
      { theme: "상태 확인", count: 12, summary: "처리 상태를 확인하기 위해 담당자 간 메시지가 이어집니다." },
      { theme: "예외 처리", count: 11, summary: "기준 밖 요청은 개인 경험에 의존해 처리됩니다." },
      { theme: "인수인계", count: 9, summary: "교대 시 진행 상황을 한눈에 넘기기 어렵습니다." },
    ],
    coverage: [
      { theme: "현장 운영", count: 92, summary: "목표 표본 대비 인터뷰 완료 비율" },
      { theme: "관리자", count: 83, summary: "목표 표본 대비 인터뷰 완료 비율" },
      { theme: "신규 담당자", count: 78, summary: "목표 표본 대비 인터뷰 완료 비율" },
      { theme: "야간 교대", count: 61, summary: "추가 모집이 필요한 표본" },
    ],
    sessionStatus: [
      { theme: "완료", count: 18, summary: "리포트 생성 가능" },
      { theme: "예약", count: 1, summary: "예정된 인터뷰" },
      { theme: "검토 필요", count: 1, summary: "응답 품질 확인 대기" },
      { theme: "미배정", count: 0, summary: "아직 배정되지 않은 세션" },
    ],
    focusedEvidence: {
      evidence: [
        {
          theme: "반복 입력",
          summary: "같은 고객·주문 정보를 여러 시스템에 다시 입력하는 흐름이 가장 많이 확인됐습니다.",
          quote: "같은 고객 정보는 요청이 끝날 때까지 세 번 입력합니다.",
          sessionCount: 8,
          nextAction: "한 번의 확인으로 입력을 재사용할 수 있는 지점을 확인하세요.",
        },
        {
          theme: "상태 확인",
          summary: "처리 상태를 찾기 위해 담당자 사이의 확인 메시지가 이어집니다.",
          quote: "명확한 상태만 보이면 운영팀에 다시 묻지 않아도 됩니다.",
          sessionCount: 6,
          nextAction: "상태와 다음 담당자를 한 화면에서 확인하는 흐름을 검증하세요.",
        },
        {
          theme: "예외 처리",
          summary: "기준 밖 요청은 개인 경험에 기대어 처리하는 경우가 많습니다.",
          quote: "예외 사유가 보이면 판단을 다시 설명할 필요가 없습니다.",
          sessionCount: 5,
          nextAction: "반복되는 예외 사유를 먼저 분류해 확인하세요.",
        },
        {
          theme: "인수인계",
          summary: "교대 시 진행 맥락을 한눈에 넘기기 어렵다는 신호가 있습니다.",
          quote: "다음 단계의 담당자가 누구인지 먼저 알아야 일을 이어갈 수 있습니다.",
          sessionCount: 4,
          nextAction: "인수인계에 필요한 최소 상태 정보를 확인하세요.",
        },
      ],
    },
    sessionThemeMap: {
      "Repeat entry": "반복 입력",
      "Ownership clarity": "인수인계",
      "Research operations": "인수인계",
    },
    highlights: [
      "반복 입력을 하나의 확인 단계로 줄이는 요구가 가장 자주 언급됐습니다.",
      "예외 기준을 문서화하면 신규 담당자의 적응 시간이 짧아질 가능성이 있습니다.",
      "야간 교대 표본을 보강하면 역할별 차이를 더 안정적으로 비교할 수 있습니다.",
    ],
  },
  {
    id: "journey-exploration",
    title: "서비스 이용 여정 탐색 조사",
    subtitle: "고객이 시작·이탈·재방문하는 순간을 이해합니다.",
    description: "가입 이후 첫 과업을 완료하는 과정에서 고객이 느끼는 망설임과 신뢰 신호를 파악하는 조사입니다.",
    status: "ready",
    updatedAt: "2026. 08. 18.",
    owner: "Customer Experience",
    sessions: { completed: 12, total: 12 },
    coverageScore: 94,
    evidenceCount: 39,
    keyFindingCount: 5,
    researchGaps: 1,
    evidence: [
      { theme: "첫 설정", count: 13, summary: "처음 보는 용어와 권한 설정에서 멈춤이 발생합니다." },
      { theme: "신뢰 신호", count: 10, summary: "저장 전 미리보기와 되돌리기 기능이 안심을 줍니다." },
      { theme: "비교 행동", count: 9, summary: "대안을 비교할 수 있는 정보가 부족하다고 느낍니다." },
      { theme: "재방문", count: 7, summary: "이전 작업 맥락을 보존할 때 재방문이 쉬워집니다." },
    ],
    coverage: [
      { theme: "첫 이용자", count: 100, summary: "목표 표본 대비 인터뷰 완료 비율" },
      { theme: "재방문자", count: 92, summary: "목표 표본 대비 인터뷰 완료 비율" },
      { theme: "이탈 경험자", count: 88, summary: "목표 표본 대비 인터뷰 완료 비율" },
      { theme: "모바일 중심", count: 96, summary: "목표 표본 대비 인터뷰 완료 비율" },
    ],
    sessionStatus: [
      { theme: "완료", count: 12, summary: "리포트 생성 가능" },
      { theme: "예약", count: 0, summary: "예정된 인터뷰" },
      { theme: "검토 필요", count: 0, summary: "응답 품질 확인 대기" },
      { theme: "미배정", count: 0, summary: "아직 배정되지 않은 세션" },
    ],
    highlights: [
      "첫 설정에서 용어 설명을 바로 제공하면 다음 단계 진입이 쉬워집니다.",
      "미리보기와 되돌리기 같은 신뢰 장치가 행동을 이어가게 합니다.",
      "모바일 이용자는 긴 비교 표보다 핵심 차이를 먼저 확인하고 싶어 합니다.",
    ],
  },
  {
    id: "feature-validation",
    title: "신규 기능 가치 검증 조사",
    subtitle: "출시 전 기능의 문제 적합성과 보완점을 검증합니다.",
    description: "프로토타입을 사용한 뒤 기대 가치, 이해 난이도, 전환 조건을 비교해 출시 판단을 돕는 조사입니다.",
    status: "processing",
    updatedAt: "2026. 08. 20.",
    owner: "Product Strategy",
    sessions: { completed: 7, total: 16 },
    coverageScore: 44,
    evidenceCount: 18,
    keyFindingCount: 3,
    researchGaps: 4,
    evidence: [
      { theme: "즉시 가치", count: 7, summary: "반복 업무를 줄일 수 있다는 점을 빠르게 이해합니다." },
      { theme: "설명 필요", count: 5, summary: "자동 추천 기준에 대한 설명을 원합니다." },
      { theme: "전환 조건", count: 4, summary: "기존 방식과 함께 쓸 수 있을 때 시도 의향이 높습니다." },
      { theme: "통제감", count: 2, summary: "결과를 수정·되돌릴 수 있어야 안심합니다." },
    ],
    coverage: [
      { theme: "핵심 사용자", count: 58, summary: "목표 표본 대비 인터뷰 완료 비율" },
      { theme: "관리자", count: 38, summary: "목표 표본 대비 인터뷰 완료 비율" },
      { theme: "도입 결정자", count: 31, summary: "목표 표본 대비 인터뷰 완료 비율" },
      { theme: "신규 사용자", count: 50, summary: "목표 표본 대비 인터뷰 완료 비율" },
    ],
    sessionStatus: [
      { theme: "완료", count: 7, summary: "리포트 생성 가능" },
      { theme: "예약", count: 5, summary: "예정된 인터뷰" },
      { theme: "검토 필요", count: 2, summary: "응답 품질 확인 대기" },
      { theme: "미배정", count: 2, summary: "아직 배정되지 않은 세션" },
    ],
    highlights: [
      "자동 추천의 기준을 보여주면 새 기능의 신뢰도를 높일 수 있습니다.",
      "기존 방식에서 자연스럽게 전환하는 흐름을 설계해야 합니다.",
      "표본이 완료되면 역할별 기대 가치의 차이를 다시 검증해야 합니다.",
    ],
  },
];
