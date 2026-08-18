import React from "react";
import PageHeader from "../components/PageHeader";
import QualitativeInterview from "../sections/services/QualitativeInterview";
import RoomDiagram from "../sections/services/RoomDiagram";
import ReportAnalysis from "../sections/services/ReportAnalysis";
import ScopeExclusion from "../sections/services/ScopeExclusion";

export const Services: React.FC = () => {
  return (
    <div className="services-page">
      <PageHeader
        title="제공하는 서비스"
        description="AI가 주도하고 사람이 보완하는 차세대 정성조사 플랫폼의 세부 모듈을 파악해 보세요."
      />
      <QualitativeInterview />
      <RoomDiagram />
      <ReportAnalysis />
      <ScopeExclusion />
    </div>
  );
};

export default Services;
