import React from "react";
import SectionHeading from "../../components/SectionHeading";
import Card from "../../components/Card";

export const SolutionSection: React.FC = () => {
  return (
    <section className="solution-section section-padding">
      <div className="container">
        <SectionHeading
          title="Gromit의 3대 솔루션"
          subtitle="AI 기술을 활용해 인터뷰 수행부터 번역, 관찰 및 개입까지 단일 워크플로우로 통합합니다."
          align="center"
        />

        <div className="solution-cards-grid">
          {/* Card 1: AI Moderator */}
          <Card variant="interactive" padding="lg" className="solution-card">
            <div className="solution-icon-wrapper">
              <svg
                width="40"
                height="40"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                <circle cx="12" cy="10" r="3"></circle>
              </svg>
            </div>
            <h3 className="solution-card-title">① AI 모더레이터 에이전트</h3>
            <p className="solution-card-text">
              메인룸 아바타가 사전에 입력된 가이드를 바탕으로 자연스럽게 대화를 유도하고 인터뷰를 매끄럽게 단독 진행합니다.
            </p>
          </Card>

          {/* Card 2: AI Simultaneous Interpreter */}
          <Card variant="interactive" padding="lg" className="solution-card">
            <div className="solution-icon-wrapper">
              <svg
                width="40"
                height="40"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="m5 8 6 6 6-6"></path>
                <path d="m4 14 6-6 8 8"></path>
                <circle cx="12" cy="12" r="10"></circle>
              </svg>
            </div>
            <h3 className="solution-card-title">② AI 동시통역 에이전트</h3>
            <p className="solution-card-text">
              응답자의 발화 내용을 실시간으로 텍스트 및 음성으로 번역하여 백룸(참관룸) 채널로 초저지연 송출합니다.
            </p>
          </Card>

          {/* Card 3: Real-time Backroom Intervention */}
          <Card variant="interactive" padding="lg" className="solution-card">
            <div className="solution-icon-wrapper">
              <svg
                width="40"
                height="40"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M2 12h20"></path>
                <path d="M20 12v8H4v-8"></path>
                <path d="m12 2-8 5v5h16V7z"></path>
              </svg>
            </div>
            <h3 className="solution-card-title">③ 참관룸(백룸) 실시간 개입</h3>
            <p className="solution-card-text">
              PM 및 클라이언트 참관자진이 실시간 스트림 화면을 시청하며, 필요시 AI 모더레이터에게 즉각 추가 지시를 전달합니다.
            </p>
          </Card>
        </div>
      </div>
    </section>
  );
};

export default SolutionSection;
