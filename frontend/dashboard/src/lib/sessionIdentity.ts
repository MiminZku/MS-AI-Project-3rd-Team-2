const PARTICIPANT_ID_PATTERN = /^[A-Z0-9-]{3,40}$/;

export function normalizeParticipantId(value: string): string {
  return value.trim().toUpperCase();
}

export function validateParticipantId(value: string): string | null {
  return PARTICIPANT_ID_PATTERN.test(normalizeParticipantId(value))
    ? null
    : "참가자 ID는 3~40자의 영문 대문자, 숫자, 하이픈만 사용할 수 있습니다.";
}

export function formatSessionReference(sessionId: string): string {
  return `인터뷰 · ${sessionId}`;
}
