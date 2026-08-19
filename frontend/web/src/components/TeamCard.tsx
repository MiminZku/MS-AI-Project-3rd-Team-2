import React from "react";
import Card from "./Card";
import { TeamMember } from "../mock/team";
import AvatarCharacter from "./AvatarCharacter";

interface TeamCardProps {
  member: TeamMember;
}

export const TeamCard: React.FC<TeamCardProps> = ({ member }) => {
  return (
    <Card variant="default" padding="lg" className="team-card">
      <div className="team-avatar-wrapper">
        <AvatarCharacter variant={member.avatarVariant} size={72} />
      </div>
      <div className="team-info">
        <h3 className="team-name">{member.name}</h3>
        <p className="team-role">{member.role}</p>
      </div>
    </Card>
  );
};

export default TeamCard;
