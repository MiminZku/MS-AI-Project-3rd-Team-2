import React from "react";
import { useRole } from "../auth/RoleContext";
import DownloadCatalog from "../components/research/DownloadCatalog";
import TopicList from "../components/research/TopicList";
import { researchProjects } from "../mock/researchProjects";
import ResearchCapabilities from "../sections/platform/ResearchCapabilities";
import ResearchHero from "../sections/platform/ResearchHero";

export const Home: React.FC = () => {
  const { role } = useRole();

  if (!role) return null;

  return (
    <div className="research-home">
      <ResearchHero />
      <section className="research-home__workspace">
        <div className="container">
          <TopicList
            projects={researchProjects}
            role={role}
            heading="지금 읽을 수 있는 조사 주제"
            description="각 주제는 독립된 결과 화면으로 이동합니다. 그 안에서 관점을 바꾸고, 필요한 산출물을 바로 저장할 수 있습니다."
          />
        </div>
      </section>
      <ResearchCapabilities />
      <section className="research-home__downloads">
        <div className="container"><DownloadCatalog /></div>
      </section>
      <section className="research-home__closing">
        <div className="container research-home__closing-inner">
          <p className="research-eyebrow">Make evidence useful</p>
          <h2>조사 결과가<br />다음 결정을 움직이게.</h2>
          <p>Gromit은 대화를 저장하는 데서 멈추지 않고, 팀이 다시 쓰는 근거와 산출물까지 연결합니다.</p>
        </div>
      </section>
    </div>
  );
};

export default Home;
