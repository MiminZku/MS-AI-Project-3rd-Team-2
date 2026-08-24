export interface ClientResearchSessionRecord {
  id: string;
  projectId: string;
  participantSegment: string;
  status: "scheduled" | "completed";
  scheduledAt: string;
  completedAt?: string;
  durationMinutes: number;
  themes: string[];
  approvedQuotes: string[];
  dashboardTheme: string;
  clientVisible: true;
}

export const clientResearchSessions: ClientResearchSessionRecord[] = [
  {
    id: "session-01",
    projectId: "workflow-discovery",
    participantSegment: "Operations lead",
    status: "completed",
    scheduledAt: "2026-08-11T09:00:00+09:00",
    completedAt: "2026-08-11T09:52:00+09:00",
    durationMinutes: 52,
    themes: ["handoff visibility", "exception handling"],
    approvedQuotes: [
      "I need to know who owns the next step before I can move the case forward.",
      "Exceptions are manageable when the reason is visible in the same place.",
    ],
    dashboardTheme: "Ownership clarity",
    clientVisible: true,
  },
  {
    id: "session-02",
    projectId: "workflow-discovery",
    participantSegment: "Customer support manager",
    status: "completed",
    scheduledAt: "2026-08-12T14:00:00+09:00",
    completedAt: "2026-08-12T14:45:00+09:00",
    durationMinutes: 45,
    themes: ["repeat entry", "status confirmation"],
    approvedQuotes: [
      "The same customer detail is entered three times before the request is complete.",
      "A clear status saves us from asking the operations team for updates.",
    ],
    dashboardTheme: "Repeat entry",
    clientVisible: true,
  },
];
