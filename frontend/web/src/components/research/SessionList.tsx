import { CalendarBlank, CaretRight, CheckCircle, Clock, FileText, PlayCircle, Tag } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useRole } from "../../auth/RoleContext";
import {
  getPermittedSessionArtifacts,
  getPmProjectSessions,
  getProjectSessions,
  type ClientResearchSession,
  type ResearchSession,
} from "../../lib/researchSessions";

type PermittedSession = ResearchSession | ClientResearchSession;

interface SessionListProps {
  projectId: string;
  selectedSessionId?: string;
  onSelect: (session: PermittedSession) => void;
}

const formatSessionTime = (timestamp?: string) =>
  timestamp
    ? new Intl.DateTimeFormat("en", {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      }).format(new Date(timestamp))
    : "Awaiting completion";

export default function SessionList({ projectId, selectedSessionId, onSelect }: SessionListProps) {
  const { role } = useRole();
  const isPm = role === "pm";
  const clientSessions = getProjectSessions(projectId);
  const [pmSessions, setPmSessions] = useState<ResearchSession[]>();

  useEffect(() => {
    if (role !== "pm") return;
    let active = true;
    void getPmProjectSessions(projectId).then((sessions) => {
      if (active) setPmSessions(sessions);
    });
    return () => { active = false; };
  }, [projectId, role]);

  const sessions = role === "pm" ? pmSessions ?? clientSessions : clientSessions;
  const activeSessionId = selectedSessionId ?? sessions[0]?.id;

  return (
    <section className="session-list" aria-labelledby="session-list-title">
      <div className="session-list__heading">
        <div>
          <p className="research-eyebrow">Interview sessions</p>
          <h2 id="session-list-title">Read the evidence behind the BI.</h2>
        </div>
        <span className="session-list__count">{sessions.length} {isPm ? "available" : "approved"}</span>
      </div>

      <div className="session-list__rows">
        {sessions.map((session) => {
          const isSelected = session.id === activeSessionId;
          const isCompleted = session.status === "completed";
          const statusText = isCompleted ? "Completed" : "Scheduled";

          return (
            <div
              className={`session-list__row${isSelected ? " is-selected" : ""}`}
              key={session.id}
            >
              <button
                type="button"
                className="session-list__select"
                onClick={() => onSelect(session)}
                aria-pressed={isSelected}
                aria-label={`${session.participantSegment} 세션 선택`}
              >
                {isPm ? <span className={`session-list__status session-list__status--${session.status}`}>
                  {isCompleted ? <CheckCircle size={17} weight="fill" /> : <CalendarBlank size={17} weight="bold" />}
                  {statusText}
                </span> : null}
                <span className="session-list__identity">
                  <strong>{session.participantSegment}</strong>
                  <small>
                    <Clock size={14} /> {session.durationMinutes} min
                    {isPm ? <><span aria-hidden="true">·</span>{formatSessionTime(isCompleted ? session.completedAt : session.scheduledAt)}</> : null}
                  </small>
                </span>
                <span className="session-list__artifacts" aria-label="Permitted artifacts">
                  {getPermittedSessionArtifacts(session, role ?? "client").map((artifact) => (
                    <small key={artifact}>
                      {artifact === "Full transcript" ? <FileText size={13} /> : artifact === "Recording" ? <PlayCircle size={13} /> : <Tag size={13} />}
                      {artifact}
                    </small>
                  ))}
                </span>
              </button>
              <Link className="session-list__detail" to={`/projects/${projectId}/sessions/${session.id}`}>
                세션 상세 <CaretRight size={17} weight="bold" aria-hidden="true" />
              </Link>
            </div>
          );
        })}
      </div>
    </section>
  );
}
