import { Database, DownloadSimple, FileDoc, LockSimple } from "@phosphor-icons/react";
import { useState } from "react";
import type { UserRole } from "../../auth/RoleContext";
import { rolePermissions } from "../../lib/roleAccess";
import type { ResearchProject } from "../../mock/researchProjects";
import { downloadPayload, makePowerBiDataset, makeWordReport } from "../../lib/researchInsights";

interface DirectDownloadsProps {
  project: ResearchProject;
  role: UserRole;
}

export default function DirectDownloads({ project, role }: DirectDownloadsProps) {
  const [notice, setNotice] = useState("");
  const isReady = project.status === "ready";
  const isAvailable = role === "client" || isReady;
  const canDownloadDataset = rolePermissions(role).viewPowerBiDataset;
  const wordReportLabel = role === "pm" ? "Full Word report" : "Executive Word report";

  const download = (kind: "word" | "dataset") => {
    if (!isAvailable || (kind === "dataset" && !canDownloadDataset)) return;
    const payload = kind === "word" ? makeWordReport(project, role) : makePowerBiDataset(project);
    downloadPayload(payload);
    setNotice(`${kind === "word" ? "Word 리포트" : "Power BI 데이터셋"} 다운로드를 시작했습니다.`);
  };

  return (
    <section className={`direct-downloads direct-downloads--${role}`} aria-labelledby="direct-downloads-title">
      <div className="direct-downloads__heading">
        <div>
          <p className="research-eyebrow">Direct download</p>
          <h2 id="direct-downloads-title">바로 받을 수 있는 산출물</h2>
          <p>프로젝트 결과를 여는 별도 창 없이, 지금 이 페이지에서 저장합니다.</p>
        </div>
        {role === "pm" && !isReady ? (
          <span className="direct-downloads__processing"><LockSimple size={16} />분석이 완료되면 활성화됩니다</span>
        ) : null}
      </div>

      <div className="direct-downloads__items">
        <article className="direct-downloads__item">
          <span className="direct-downloads__icon"><FileDoc size={25} weight="duotone" /></span>
          <div>
            <h3>{wordReportLabel}</h3>
            <p>{role === "pm" ? "의사결정 근거와 조사 운영 맥락을 포함한 내부용 Word 리포트입니다." : "핵심 인사이트와 승인된 근거만 정리한 전달용 Word 리포트입니다."}</p>
            <small>.doc · 브라우저에서 생성</small>
          </div>
          <button type="button" disabled={!isAvailable} onClick={() => download("word")}>
            <DownloadSimple size={18} weight="bold" />Word 다운로드
          </button>
        </article>

        {canDownloadDataset ? (
          <article className="direct-downloads__item">
            <span className="direct-downloads__icon"><Database size={25} weight="duotone" /></span>
            <div>
              <h3>Power BI dataset</h3>
              <p>주제별 Evidence를 필터·조합할 수 있도록 정리한 운영용 Power BI 데이터셋입니다.</p>
              <small>.csv · Power BI에서 바로 불러오기</small>
            </div>
            <button type="button" disabled={!isAvailable} onClick={() => download("dataset")}>
              <DownloadSimple size={18} weight="bold" />BI 데이터 다운로드
            </button>
          </article>
        ) : null}
      </div>
      <p className="direct-downloads__notice" aria-live="polite">{notice}</p>
    </section>
  );
}
