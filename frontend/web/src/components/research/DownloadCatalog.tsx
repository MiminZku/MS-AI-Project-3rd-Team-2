import { CaretRight, Database, FileDoc } from "@phosphor-icons/react";
import { Link } from "react-router-dom";
import { useRole } from "../../auth/RoleContext";
import { rolePermissions } from "../../lib/roleAccess";

interface DownloadCatalogProps {
  expanded?: boolean;
}

export default function DownloadCatalog({ expanded = false }: DownloadCatalogProps) {
  const { role } = useRole();
  const canViewDataset = role === "pm" && rolePermissions(role).viewPowerBiDataset;
  const catalogItems = [
    {
      icon: FileDoc,
      title: role === "pm" ? "Full Word report" : "Executive Word report",
      description: role === "pm" ? "의사결정 근거와 조사 운영 맥락을 담은 내부용 리포트" : "승인된 핵심 인사이트를 담은 전달용 리포트",
      type: "Word",
    },
    ...(canViewDataset ? [{ icon: Database, title: "Power BI dataset", description: "시각화와 재분석을 위한 운영용 데이터", type: "CSV" }] : []),
  ];
  const visibleItems = expanded ? catalogItems : catalogItems.slice(0, 2);

  return (
    <section className="download-catalog" aria-labelledby="download-catalog-title">
      <div className="research-section-heading research-section-heading--row">
        <div>
          <p className="research-eyebrow">Download center</p>
          <h2 id="download-catalog-title">산출물 목록</h2>
          <p>{role === "pm" ? "조사 결과와 운영용 분석 자료를 확인하고 저장할 수 있습니다." : "전달 가능한 핵심 결과 리포트를 확인하고 저장할 수 있습니다."}</p>
        </div>
        {!expanded ? <Link to="/downloads" className="research-text-link">전체 목록 <CaretRight size={16} weight="bold" /></Link> : null}
      </div>

      <div className="download-catalog__rows">
        {visibleItems.map((item) => {
          const Icon = item.icon;
          const rowContents = <>
              <span className="download-catalog__icon"><Icon size={22} weight="duotone" /></span>
              <span className="download-catalog__copy"><strong>{item.title}</strong><span>{item.description}</span></span>
              <span className="download-catalog__type">{item.type}</span>
              <CaretRight size={19} aria-hidden="true" />
            </>;

          return <Link className="download-catalog__row download-catalog__row--available" to="/downloads" key={item.title}>{rowContents}</Link>;
        })}
      </div>
    </section>
  );
}
