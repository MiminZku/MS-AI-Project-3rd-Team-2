import { ArrowRight, CheckCircle, DownloadSimple, FileDoc } from "@phosphor-icons/react";
import { Link } from "react-router-dom";
import { useRole } from "../auth/RoleContext";
import DownloadCatalog from "../components/research/DownloadCatalog";
import { researchProjects } from "../mock/researchProjects";

export default function Downloads() {
  const { role } = useRole();
  const isPm = role === "pm";

  return (
    <div className="research-page research-download-page">
      <section className="research-page-hero research-page-hero--light">
        <div className="container">
          <p className="research-eyebrow">Download center</p>
          <h1>조사의 결과를<br />필요한 형식으로.</h1>
          <p>{isPm ? "Save reports and analysis data directly from each research result." : "Save delivery-ready reports directly from each research result."}</p>
        </div>
      </section>

      <main className="research-page__body container">
        <DownloadCatalog expanded />
        <section className="research-download-projects" aria-labelledby="download-project-title">
          <div className="research-section-heading research-section-heading--row">
          <div><p className="research-eyebrow">By research topic</p><h2 id="download-project-title">어떤 조사에서 받을까요?</h2></div>
            {isPm ? <span><DownloadSimple size={18} />결과 준비 프로젝트부터 이용 가능</span> : null}
          </div>
          <div className="research-download-projects__rows">
            {researchProjects.map((project) => {
              const isReady = project.status === "ready";
              return (
                <Link to={`/projects/${project.id}/results`} key={project.id} className="research-download-projects__row">
                  <span className="research-download-projects__icon"><FileDoc size={21} weight="duotone" /></span>
                  <span><strong>{project.title}</strong><small>{isPm ? `${project.sessions.completed}/${project.sessions.total} 세션 · ` : ""}{project.evidenceCount} Evidence</small></span>
                  {isPm ? <span className={isReady ? "research-download-projects__ready" : "research-download-projects__waiting"}>{isReady ? <><CheckCircle size={16} weight="fill" />다운로드 가능</> : "분석 중"}</span> : null}
                  <ArrowRight size={18} weight="bold" />
                </Link>
              );
            })}
          </div>
        </section>
      </main>
    </div>
  );
}
