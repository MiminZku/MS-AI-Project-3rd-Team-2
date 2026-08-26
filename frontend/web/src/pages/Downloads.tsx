import { ArrowRight, CheckCircle, DownloadSimple, FileDoc, Lock } from "@phosphor-icons/react";
import { Link } from "react-router-dom";
import { useRole } from "../auth/RoleContext";
import DownloadCatalog from "../components/research/DownloadCatalog";
import ProjectDownloadCenter from "../components/research/ProjectDownloadCenter";
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

        {/* 실제 백엔드와 연동된 다운로드 영역.
            클라이언트는 Project Access ID 화면에서 같은 파일을 받을 수 있다. */}
        {isPm ? (
          <ProjectDownloadCenter />
        ) : (
          <section className="download-center">
            <p className="download-center__empty">
              <Lock size={16} weight="fill" /> 클라이언트는 발급받은 Project Access ID로 입장하면
              해당 프로젝트의 리포트와 인터뷰 자료를 받을 수 있습니다.{" "}
              <Link to="/client/access">Project Access ID 입력하기</Link>
            </p>
          </section>
        )}

        <section className="research-download-projects" aria-labelledby="download-project-title">
          <div className="research-section-heading research-section-heading--row">
          <div><p className="research-eyebrow">Sample showcase</p><h2 id="download-project-title">결과 화면 미리보기 (샘플)</h2></div>
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
