import React from "react";
import PageHeader from "../components/PageHeader";
import { teamMembers } from "../mock/team";
import TeamCard from "../components/TeamCard";

export const Team: React.FC = () => {
  return (
    <div className="team-page">
      <PageHeader
        title="우리 팀원"
        description="Gromit 솔루션을 설계하고 구축하는 프로젝트 팀원들을 소개합니다."
        className="section--dark"
      />
      <section className="team-section-list section-padding">
        <div className="container">
          <div className="team-cards-grid">
            {teamMembers.map((member, idx) => (
              <TeamCard key={idx} member={member} />
            ))}
          </div>
        </div>
      </section>
    </div>
  );
};

export default Team;
