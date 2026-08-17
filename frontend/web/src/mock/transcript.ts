export interface TranscriptTurn {
  id: string;
  speaker: "moderator" | "respondent";
  speakerName: string;
  timestamp: string;
  originalText: string;
  translatedText: string;
}

export const mockTranscript: TranscriptTurn[] = [
  {
    id: "turn-1",
    speaker: "moderator",
    speakerName: "AI Moderator",
    timestamp: "00:15",
    originalText: "안녕하세요! 오늘 인터뷰에 참여해 주셔서 감사합니다. 먼저 평소에 스마트 가전을 얼마나 자주 사용하시는지 말씀해 주세요.",
    translatedText: "Hello! Thank you for participating in the interview today. First, please tell me how often you usually use smart home appliances."
  },
  {
    id: "turn-2",
    speaker: "respondent",
    speakerName: "응답자 A",
    timestamp: "00:48",
    originalText: "음, 저는 인공지능 세탁기하고 로봇 청소기를 거의 매일 쓰고 있어요. 특히 로봇 청소기는 출근할 때 켜두고 나가서 정말 자주 씁니다.",
    translatedText: "Well, I use the AI washing machine and robot vacuum cleaner almost every day. Especially the robot vacuum, I turn it on when I go to work, so I use it very often."
  },
  {
    id: "turn-3",
    speaker: "moderator",
    speakerName: "AI Moderator",
    timestamp: "01:20",
    originalText: "매일 사용하고 계시는군요. 스마트 가전을 사용할 때 가장 편리하다고 느끼는 기능은 어떤 부분인가요?",
    translatedText: "So you use them every day. What features do you find most convenient when using smart home appliances?"
  },
  {
    id: "turn-4",
    speaker: "respondent",
    speakerName: "응답자 A",
    timestamp: "01:55",
    originalText: "아무래도 손을 대지 않고 앱이나 음성으로 컨트롤할 수 있는 부분이 제일 편해요. 요리하거나 설거지할 때 유용하더라고요.",
    translatedText: "By all means, being able to control it with an app or voice without hands is the most convenient. It's useful when cooking or doing dishes."
  },
  {
    id: "turn-5",
    speaker: "moderator",
    speakerName: "AI Moderator",
    timestamp: "02:30",
    originalText: "그렇다면 반대로 사용하시면서 가장 불편했거나 프라이버시적인 측면에서 우려되었던 경험이 있으신가요?",
    translatedText: "On the other hand, did you experience any inconvenience or have any concerns regarding privacy while using them?"
  },
  {
    id: "turn-6",
    speaker: "respondent",
    speakerName: "응답자 A",
    timestamp: "03:15",
    originalText: "가끔 혼자 있을 때 기기가 갑자기 제 목소리도 아닌데 오작동해서 켜질 때가 있어요. 혹시 제 대화 소리를 몰래 수집하고 있나 걱정이 됐어요.",
    translatedText: "Sometimes, when I'm alone, the device turns on accidentally even though it's not my voice. I was worried that it might be secretly collecting my conversations."
  }
];
