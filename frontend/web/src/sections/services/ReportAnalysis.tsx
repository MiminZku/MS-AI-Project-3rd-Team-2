import React from "react";
import SectionHeading from "../../components/SectionHeading";
import TranscriptExportCard from "../../components/report/TranscriptExportCard";
import AnalysisDashboardPreview from "../../components/report/AnalysisDashboardPreview";

export const ReportAnalysis: React.FC = () => {
  return (
    <section className="report-analysis-section section-padding section--dark">
      <div className="container">
        <SectionHeading
          title="② 조사 리포트 분석 & 최종 산출물"
          subtitle="인터뷰 종료 후 실시간으로 취합된 데이터를 바탕으로 원문/번역 텍스트 다운로드 및 핵심 메트릭 분석 리포트 화면을 제공합니다."
        />

        <div className="report-mockups-container">
          {/* Output 1: Transcript switcher & exporter card */}
          <div className="mockup-item">
            <TranscriptExportCard />
          </div>

          {/* Output 2: Native SVG metrics chart & quote dashboard preview */}
          <div className="mockup-item report-preview-item">
            <AnalysisDashboardPreview />
          </div>
        </div>
      </div>
    </section>
  );
};

export default ReportAnalysis;
