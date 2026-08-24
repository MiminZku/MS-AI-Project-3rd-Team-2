import { expect, it } from "vitest";
import { getPmSessionTranscript } from "./pmSessionTranscripts";

it("returns transcript evidence only for the matching PM session", () => {
  expect(getPmSessionTranscript("session-01")).toHaveLength(6);
  expect(getPmSessionTranscript("session-04")).toBeUndefined();
});
