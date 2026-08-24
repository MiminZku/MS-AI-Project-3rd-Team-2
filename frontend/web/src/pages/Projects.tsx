import { ArrowRight, FolderOpen, Plus } from "@phosphor-icons/react";
import { Link, Navigate } from "react-router-dom";
import { useRole } from "../auth/RoleContext";
import TopicList from "../components/research/TopicList";
import { researchProjects } from "../mock/researchProjects";

export default function Projects() {
  const { role } = useRole();
  const readyCount = researchProjects.filter((project) => project.status === "ready").length;
  const isPm = role === "pm";

  if (!isPm) {
    return <Navigate to="/client/access" replace />;
  }

  return (
    <div className="research-page">
      <section className="research-page-hero research-page-hero--dark">
        <div className="container">
          <p className="research-eyebrow">Research workspace</p>
          <div className="research-page-hero__row">
            <div><h1>프로젝트마다<br />독립적인 조사 공간.</h1><p>가이드, 인터뷰, 결과, 산출물을 주제별로 나누어 관리합니다.</p></div>
            <a className="research-button research-button--primary" href="/dashboard/"><Plus size={18} weight="bold" />새 조사 만들기</a>
          </div>
        </div>
      </section>

      <section className="research-page__body container">
        <div className="research-workspace-summary">
          <span><FolderOpen size={22} weight="duotone" /></span>
          <div><strong>{isPm ? `${researchProjects.length}개 프로젝트` : "Research delivery"}</strong><p>{isPm ? `${readyCount}개 결과 준비됨 · 진행 중인 조사는 계속 업데이트됩니다.` : "승인된 근거와 핵심 인사이트를 주제별로 확인할 수 있습니다."}</p></div>
          <Link to="/downloads">다운로드 센터 <ArrowRight size={16} weight="bold" /></Link>
        </div>
        {role ? <TopicList projects={researchProjects} role={role} heading="Research projects" description="주제를 선택하면 해당 조사만의 시각화와 직접 다운로드를 확인할 수 있습니다." /> : null}
      </section>
    </div>
  );
}
