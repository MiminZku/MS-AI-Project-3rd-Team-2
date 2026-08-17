export interface KeyTopic {
  id: string;
  topic: string;
  count: number;
  sentiment: "positive" | "neutral" | "negative";
}

export interface RespondentQuote {
  id: string;
  quote: string;
  timestamp: string;
  speaker: string;
  sentiment: "positive" | "neutral" | "negative";
}

export interface SummaryCard {
  title: string;
  content: string;
}

export interface AnalysisReport {
  sessionId: string;
  title: string;
  date: string;
  durationMinutes: number;
  totalTurnCount: number;
  summaryCards: SummaryCard[];
  keyTopics: KeyTopic[];
  quotes: RespondentQuote[];
  satisfactionData: {
    category: string;
    score: number;
  }[];
}

export const mockAnalysisReport: AnalysisReport = {
  sessionId: "session-2026-08-18-001",
  title: "AI 스마트 가전 브랜드 인지도 및 사용성 심층 인터뷰",
  date: "2026-08-18",
  durationMinutes: 45,
  totalTurnCount: 38,
  summaryCards: [
    {
      title: "핵심 결론",
      content: "응답자들은 음성 인식 가전의 편리함에 높은 점수를 주었으나, 오동작 시의 대처 방안 부재와 프라이버시 노출 우려에 대해 높은 불안감을 보였습니다."
    },
    {
      title: "긍정 요인",
      content: "손을 쓰지 않고 기기를 조작할 수 있는 '핸즈프리' 시나리오(예: 요리 중 작동)에서 압도적인 사용자 경험 만족도를 나타냈습니다."
    },
    {
      title: "개선 필요 요인",
      content: "특정 고유명사나 사투리 억양을 인식하지 못할 때 발생하는 피로도를 최소화하고, 초기 연결(페어링) 속도를 개선해야 합니다."
    }
  ],
  keyTopics: [
    { id: "topic-1", topic: "음성 인식 만족도", count: 18, sentiment: "positive" },
    { id: "topic-2", topic: "개인정보 보호 우려", count: 12, sentiment: "negative" },
    { id: "topic-3", topic: "초기 연결 난이도", count: 9, sentiment: "negative" },
    { id: "topic-4", topic: "디자인 및 외관", count: 8, sentiment: "positive" },
    { id: "topic-5", topic: "고유명사 오인식", count: 6, sentiment: "neutral" }
  ],
  quotes: [
    {
      id: "quote-1",
      quote: "요리하다가 손에 양념이 묻었을 때 말로 가스레인지 불을 끄거나 레시피를 물어볼 수 있어서 정말 신세계였어요.",
      timestamp: "12:45",
      speaker: "응답자 A (30대 여)",
      sentiment: "positive"
    },
    {
      id: "quote-2",
      quote: "거실에서 일상적인 대화를 나누고 있을 때에도 기기가 갑자기 작동해서 내 사생활을 엿듣고 있는 건 아닌가 하는 찜찜함이 있어요.",
      timestamp: "24:18",
      speaker: "응답자 B (20대 남)",
      sentiment: "negative"
    },
    {
      id: "quote-3",
      quote: "스마트폰 어플하고 기기를 처음 연동할 때 자꾸 끊기고 블루투스 인식이 안 돼서 시작하기 전부터 너무 스트레스 받았습니다.",
      timestamp: "05:12",
      speaker: "응답자 A (30대 여)",
      sentiment: "negative"
    },
    {
      id: "quote-4",
      quote: "AI 스피커를 살 때는 음성 조작이 어설플 줄 알았는데, 생각보다 문장을 잘 알아듣고 부드럽게 피드백이 와서 놀랐습니다.",
      timestamp: "38:09",
      speaker: "응답자 C (40대 남)",
      sentiment: "positive"
    }
  ],
  satisfactionData: [
    { category: "음성 인식", score: 85 },
    { category: "동작 반응", score: 72 },
    { category: "보안 신뢰", score: 48 },
    { category: "디자인", score: 90 },
    { category: "연결 속도", score: 60 }
  ]
};
