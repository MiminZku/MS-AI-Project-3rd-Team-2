import { ArrowUpRight, CheckCircle, Clock } from "@phosphor-icons/react";
import { Link } from "react-router-dom";
import type { UserRole } from "../../auth/RoleContext";
import type { ResearchProject } from "../../mock/researchProjects";

interface TopicListProps {
  projects: ResearchProject[];
  heading?: string;
  description?: string;
  compact?: boolean;
  role: UserRole;
}

export default function TopicList({ projects, heading, description, compact = false, role }: TopicListProps) {
  const isPm = role === "pm";
  return (
    <section className={`research-topic-list ${compact ? "research-topic-list--compact" : ""}`}>
      {heading ? (
        <div className="research-section-heading">
          <p className="research-eyebrow">Research workspace</p>
          <h2>{heading}</h2>
          {description ? <p>{description}</p> : null}
        </div>
      ) : null}

      <div className="research-topic-rows">
        {projects.map((project, index) => {
          const isReady = project.status === "ready";

          return (
            <Link
              className="research-topic-row"
              key={project.id}
              to={`/projects/${project.id}/results`}
              aria-label={`${project.title} 결과 보기`}
            >
              <span className="research-topic-number">{String(index + 1).padStart(2, "0")}</span>
              <span className="research-topic-copy">
                <span className="research-topic-title-line">
                  <strong>{project.title}</strong>
                  {isPm ? <span className={`research-status research-status--${project.status}`}>
                    {isReady ? <CheckCircle size={15} weight="fill" /> : <Clock size={15} weight="bold" />}
                    {isReady ? "결과 준비됨" : "분석 중"}
                  </span> : null}
                </span>
                <span>{project.subtitle}</span>
              </span>
              <span className="research-topic-meta">
                {isPm ? <span>{project.sessions.completed}/{project.sessions.total} 세션</span> : null}
                <span>{project.evidenceCount} Evidence</span>
              </span>
              <ArrowUpRight className="research-topic-arrow" size={22} aria-hidden="true" />
            </Link>
          );
        })}
      </div>
    </section>
  );
}
