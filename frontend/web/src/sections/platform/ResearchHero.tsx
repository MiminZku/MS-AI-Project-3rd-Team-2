import { ArrowRight, ChartDonut, FileArrowUp, UsersThree } from "@phosphor-icons/react";
import { Link } from "react-router-dom";
import { useRole } from "../../auth/RoleContext";

export default function ResearchHero() {
  const { role } = useRole();
  const isPm = role === "pm";

  return (
    <section className="research-hero">
      <div className="container research-hero__grid">
        <div className="research-hero__copy">
          <p className="research-eyebrow">Research Workspace</p>
          <h1>의사결정에 필요한<br />사람의 목소리를<br /><em>한 화면에.</em></h1>
          <p className="research-hero__description">가이드 업로드부터 인터뷰 운영, 근거 기반 리포트와 다운로드까지. Gromit이 조사 흐름을 하나의 워크스페이스로 연결합니다.</p>
          <div className="research-hero__actions">
            <Link className="research-button research-button--primary" to="/projects">프로젝트 보기 <ArrowRight size={18} weight="bold" /></Link>
            {role === "pm"
              ? <Link className="research-button research-button--quiet" to="/services">인터뷰 운영 보기</Link>
              : <Link className="research-button research-button--quiet" to="/downloads">승인된 산출물 보기</Link>}
          </div>
        </div>

        <div className="research-hero__preview" aria-label="조사 워크스페이스 미리보기">
          <div className="research-hero__preview-top"><span>Gromit Research</span><span>{isPm ? "Live workspace" : "Delivery workspace"}</span></div>
          <div className="research-hero__preview-main">
            <div className="research-hero__preview-card research-hero__preview-card--wide">
              <span className="preview-icon"><ChartDonut size={20} weight="duotone" /></span>
              <p>Research results</p>
              <strong>47 Evidence</strong>
              <div className="preview-spark"><i /><i /><i /><i /><i /><i /></div>
            </div>
            {isPm ? <><div className="research-hero__preview-card"><span className="preview-icon"><UsersThree size={20} weight="duotone" /></span><p>Sessions</p><strong>18 / 20</strong></div><div className="research-hero__preview-card"><span className="preview-icon"><FileArrowUp size={20} weight="duotone" /></span><p>Downloads</p><strong>2 ready</strong></div></> : <><div className="research-hero__preview-card"><span className="preview-icon"><UsersThree size={20} weight="duotone" /></span><p>Approved evidence</p><strong>Key findings</strong></div><div className="research-hero__preview-card"><span className="preview-icon"><FileArrowUp size={20} weight="duotone" /></span><p>Delivery report</p><strong>Approved</strong></div></>}
          </div>
          <div className="research-hero__preview-bottom"><span>Evidence is connected to every decision.</span><i /></div>
        </div>
      </div>
    </section>
  );
}
