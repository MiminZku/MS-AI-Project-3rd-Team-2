import React from "react";
import PageHeader from "../components/PageHeader";
import MissionSection from "../sections/about/MissionSection";
import MarketSection from "../sections/about/MarketSection";
import BackgroundSection from "../sections/about/BackgroundSection";
import TrustSection from "../sections/about/TrustSection";

export const About: React.FC = () => {
  return (
    <div className="about-page">
      <PageHeader
        title="About Us"
        description="인공지능과 사람이 협업하는 차세대 정성조사 환경을 만들어 갑니다."
        className="section--dark"
      />
      <MissionSection />
      <MarketSection />
      <BackgroundSection />
      <TrustSection />
    </div>
  );
};

export default About;
