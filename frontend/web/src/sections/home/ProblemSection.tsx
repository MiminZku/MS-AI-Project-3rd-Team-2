import React from "react";
import SectionHeading from "../../components/SectionHeading";
import StatBlock from "../../components/StatBlock";
import Card from "../../components/Card";

export const ProblemSection: React.FC = () => {
  return (
    <section className="problem-section section-padding">
      <div className="container">
        <SectionHeading
          title="기존 정성조사가 직면한 두 가지 한계"
          subtitle="시간과 비용의 문제를 획기적으로 낮추지 못하면 진정한 데이터 인사이트를 적시에 얻을 수 없습니다."
          align="center"
        />

        <div className="problem-stats-grid">
          <Card variant="default" padding="lg">
            <StatBlock
              value="최소 1~2주"
              label="① 시간 조율의 병목"
              description="통역사 · 클라이언트 · 모더레이터 · 응답자 4자의 비대면/대면 일정을 맞추는 데 최소 1~2주의 조율 기간이 강제 소요됩니다."
            />
          </Card>

          <Card variant="default" padding="lg">
            <StatBlock
              value="$200 ~ 400"
              label="② 높은 비용 구조"
              description="글로벌 조사를 동반하는 경우, 해외 응답자와 통역사 등의 인적 자원 투입으로 인해 시간당 수백 달러의 비용이 추가 발생합니다."
            />
          </Card>
        </div>
      </div>
    </section>
  );
};

export default ProblemSection;
