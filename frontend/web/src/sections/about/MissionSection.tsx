import React from "react";
import SectionHeading from "../../components/SectionHeading";

export const MissionSection: React.FC = () => {
  return (
    <section className="mission-section section-padding">
      <div className="container">
        <SectionHeading
          title="우리의 미션"
          subtitle="정성조사의 패러다임을 바꿉니다."
        />
        <div className="mission-content">
          <p className="mission-highlight">
            "메인룸에서 자연스러운 인터뷰, 동시에 백룸에서 언제든 개입 가능한 장치"
          </p>
          <p className="mission-description">
            Gromit은 응답자가 인공지능 모더레이터와 거부감 없이 매끄러운 1:1 대화를 진행하게 돕는 메인룸 환경을 설계합니다. 
            그와 동시에 실무 담당자가 언제든 참관하고 인터뷰 진행 중 실시간으로 직접 개입하여 심도 깊은 정성조사를 
            이끌어낼 수 있는 견고한 보완 장치를 백룸을 통해 동시 제공하는 것을 최고의 가치로 삼고 있습니다.
          </p>
        </div>
      </div>
    </section>
  );
};

export default MissionSection;
