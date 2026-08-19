export interface TeamMember {
  name: string;
  role: string;
  avatarVariant: 1 | 2 | 3 | 4;
}

export const teamMembers: TeamMember[] = [
  {
    name: "김은향",
    role: "Discussion Guide 설계 · 유저플로우 · 메인룸 UX",
    avatarVariant: 1,
  },
  {
    name: "장다희",
    role: "분석 파트 · 리포트 구성 · 모의 대본 데이터 수집",
    avatarVariant: 2,
  },
  {
    name: "박성은",
    role: "백룸 설계 · 와이어프레임 · STT 검증",
    avatarVariant: 3,
  },
  {
    name: "강민기",
    role: "백엔드 · 동시통역 에이전트 · 진행자 에이전트 · Git repo 관리",
    avatarVariant: 4,
  },
];
