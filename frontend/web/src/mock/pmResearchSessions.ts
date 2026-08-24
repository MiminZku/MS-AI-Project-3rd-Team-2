import type { ResearchSession } from "../lib/researchSessions";

export const pmResearchSessions: ResearchSession[] = [
  {
    id: "session-01", projectId: "workflow-discovery", participantSegment: "Operations lead", status: "completed", scheduledAt: "2026-08-11T09:00:00+09:00", completedAt: "2026-08-11T09:52:00+09:00", durationMinutes: 52,
    themes: ["handoff visibility", "exception handling"], approvedQuotes: ["I need to know who owns the next step before I can move the case forward.", "Exceptions are manageable when the reason is visible in the same place."],
    pmNote: "Strong evidence for a single handoff owner and reason-coded exceptions.", dashboardTheme: "Ownership clarity", clientVisible: true, hasTranscript: true,
  },
  {
    id: "session-02", projectId: "workflow-discovery", participantSegment: "Customer support manager", status: "completed", scheduledAt: "2026-08-12T14:00:00+09:00", completedAt: "2026-08-12T14:45:00+09:00", durationMinutes: 45,
    themes: ["repeat entry", "status confirmation"], approvedQuotes: ["The same customer detail is entered three times before the request is complete.", "A clear status saves us from asking the operations team for updates."],
    pmNote: "Prioritize deduplicated customer context and a shared status vocabulary.", dashboardTheme: "Repeat entry", clientVisible: true, hasTranscript: false,
  },
  {
    id: "session-03", projectId: "workflow-discovery", participantSegment: "Internal observer", status: "completed", scheduledAt: "2026-08-13T11:00:00+09:00", completedAt: "2026-08-13T11:36:00+09:00", durationMinutes: 36,
    themes: ["moderation check", "research protocol"], approvedQuotes: [],
    pmNote: "Operational review only; do not distribute participant-level findings.", dashboardTheme: "Research operations", clientVisible: false, hasTranscript: false,
  },
  {
    id: "session-04", projectId: "workflow-discovery", participantSegment: "Regional coordinator", status: "scheduled", scheduledAt: "2026-08-26T16:00:00+09:00", durationMinutes: 50,
    themes: ["regional handoff", "queue prioritization"], approvedQuotes: [],
    pmNote: "Recruitment confirmed; moderator guide still needs final approval.", dashboardTheme: "Priority rules", clientVisible: false, hasTranscript: false,
  },
];
