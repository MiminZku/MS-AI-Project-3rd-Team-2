import { expect, it } from "vitest";
import { formatSessionReference, normalizeParticipantId, validateParticipantId } from "./sessionIdentity";

it("normalizes and accepts anonymous participant IDs", () => {
  expect(normalizeParticipantId(" int-001 ")).toBe("INT-001");
  expect(validateParticipantId(" int-001 ")).toBeNull();
});

it("rejects person-name and malformed participant IDs", () => {
  expect(validateParticipantId("김민수")).toContain("영문 대문자");
  expect(validateParticipantId("INT 001")).toContain("영문 대문자");
});

it("formats an existing interview using only its immutable server ID", () => {
  expect(formatSessionReference("8f9c-11")).toBe("인터뷰 · 8f9c-11");
});
