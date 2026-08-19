import React from "react";
import SectionHeading from "../../components/SectionHeading";
import Card from "../../components/Card";

export const MarketSection: React.FC = () => {
  return (
    <section className="market-section section-padding">
      <div className="container">
        <SectionHeading
          title="시장 및 타겟"
          subtitle="우리가 주목하고 함께하고자 하는 정성조사 시장의 세그먼트입니다."
        />
        
        <div className="market-cards-grid">
          <Card variant="default" padding="lg">
            <h3 className="market-card-title">글로벌 시장조사 시장 타겟</h3>
            <p className="market-card-text">
              Gromit은 특정 국가에 한정되지 않고, 전 세계 다국어 조사 수요가 빈번한 글로벌 시장조사 및 정성 연구 영역을 타겟으로 삼고 있습니다. 
              초저지연 오디오 기술과 번역 에이전트를 결합하여 언어적 한계를 없애는 서비스를 제공합니다.
            </p>
          </Card>

          <Card variant="default" padding="lg">
            <h3 className="market-card-title">B2B 타겟 세그먼트</h3>
            <p className="market-card-text">
              국내외 중소 시장조사 기관 및 독립 모더레이터 중 정성조사(FGI, IDI) 수행 경력을 보유하고 있는 전문 그룹이 주요 대상입니다. 
              인력과 예산의 제한 속에서도 대기업 수준의 고효율·고품질의 조사를 완수할 수 있도록 뒷받침합니다.
            </p>
          </Card>
        </div>
      </div>
    </section>
  );
};

export default MarketSection;
