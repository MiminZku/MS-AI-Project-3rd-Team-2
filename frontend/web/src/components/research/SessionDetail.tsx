import { ChatCircleText, FileText, Quotes, Sparkle } from "@phosphor-icons/react";
import { useEffect, useState, type ComponentType } from "react";
import type { ClientResearchSession, ResearchSession } from "../../lib/researchSessions";

interface SessionDetailProps {
  role: "pm" | "client";
  session: ResearchSession | ClientResearchSession;
}

const formatDateTime = (timestamp?: string) =>
  timestamp
    ? new Intl.DateTimeFormat("en", { weekday: "short", month: "long", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(timestamp))
    : "Scheduled session";

export function SessionSummary({ session }: { session: ClientResearchSession }) {
  return <header className="session-detail__header"><p className="research-eyebrow">Session evidence</p><h1>{session.participantSegment}</h1><div className="session-detail__metadata"><span>{session.status === "completed" ? "Completed" : "Scheduled"}</span><span>{session.durationMinutes} minutes</span><span>{formatDateTime(session.completedAt ?? session.scheduledAt)}</span></div></header>;
}

export function EvidenceCards({ session }: { session: ClientResearchSession }) {
  return <section className="session-evidence" aria-labelledby="session-evidence-title"><div className="session-section-heading"><Sparkle size={21} weight="duotone" /><div><p className="research-eyebrow">Approved evidence</p><h2 id="session-evidence-title">Themes and approved quotes</h2></div></div><div className="session-evidence__grid"><article><ChatCircleText size={21} weight="duotone" /><h3>Themes</h3><ul>{session.themes.map((theme) => <li key={theme}>{theme}</li>)}</ul></article><article><Quotes size={21} weight="duotone" /><h3>Approved quotes</h3>{session.approvedQuotes.length ? <div className="session-approved-quotes">{session.approvedQuotes.map((quote) => <blockquote key={quote}>“{quote}”</blockquote>)}</div> : <p>No approved quotes are available for this session.</p>}</article></div></section>;
}

export function ClientSessionDetail({ session }: { session: ClientResearchSession }) {
  const digest = `This approved session digest centers on ${session.themes.join(" and ")}. It is prepared for project decisions without exposing operational research materials.`;
  return <><SessionSummary session={session} /><section className="session-approved-digest" aria-labelledby="approved-digest-title"><span><Sparkle size={23} weight="duotone" /></span><div><p className="research-eyebrow">Client delivery</p><h2 id="approved-digest-title">Approved session digest</h2><p>{digest}</p></div></section><EvidenceCards session={session} /><aside className="session-safe-artifacts" aria-label="Available approved artifacts"><FileText size={21} weight="duotone" /><div><strong>Safe artifact panel</strong><p>This delivery includes the approved digest, quotes, and themes only.</p></div></aside></>;
}

type PmSessionDetailComponent = ComponentType<{ session: ResearchSession }>;

export default function SessionDetail({ role, session }: SessionDetailProps) {
  const [PmSessionDetail, setPmSessionDetail] = useState<PmSessionDetailComponent>();

  useEffect(() => {
    if (role !== "pm") return;
    let active = true;
    void import("./PmSessionDetail").then(({ default: Component }) => {
      if (active) setPmSessionDetail(() => Component);
    });
    return () => { active = false; };
  }, [role]);

  if (role === "client") return <ClientSessionDetail session={session as ClientResearchSession} />;
  if (PmSessionDetail) return <PmSessionDetail session={session as ResearchSession} />;
  return <><SessionSummary session={session} /><p className="session-detail__loading">Loading PM session workspace…</p></>;
}
