import React from "react";
import SectionHeading from "../../components/SectionHeading";

interface StepItemProps {
  number: string;
  title: string;
  description: string;
}

const StepItem: React.FC<StepItemProps> = ({ number, title, description }) => {
  return (
    <div className="how-step-card">
      <div className="step-number-badge">{number}</div>
      <h3 className="step-title">{title}</h3>
      <p className="step-description">{description}</p>
    </div>
  );
};

export const HowItWorksSection: React.FC = () => {
  const steps = [
    {
      number: "01",
      title: "세션 생성",
      description: "프로젝트 정보 및 가이드를 토대로 인터뷰 질문 세션을 생성합니다.",
    },
    {
      number: "02",
      title: "인터뷰 진행 (메인룸)",
      description: "AI 에이전트가 음성 및 아바타를 활용하여 응답자와 실시간 인터뷰를 개시합니다.",
    },
    {
      number: "03",
      title: "실시간 참관 · 개입 (백룸)",
      description: "PM과 참관인이 자막/음성을 모니터링하며 필요시 질문 개입을 수행합니다.",
    },
    {
      number: "04",
      title: "리포트 · 산출물 자동 생성",
      description: "인터뷰 종료 즉시 전체 텍스트 트랜스크립트와 핵심 분석 리포트를 자동으로 취합합니다.",
    },
  ];

  return (
    <section className="how-it-works-section section-padding">
      <div className="container">
        <SectionHeading
          title="정성조사 동작 흐름"
          subtitle="프로젝트 기획부터 분석까지, 총 4단계의 고도화된 가로 타임라인 워크플로우를 확인하세요."
          align="center"
        />

        <div className="how-steps-timeline">
          {steps.map((step, idx) => (
            <React.Fragment key={idx}>
              <StepItem
                number={step.number}
                title={step.title}
                description={step.description}
              />
              {idx < steps.length - 1 && (
                <div className="step-connector desktop-only" aria-hidden="true">
                  <span className="connector-arrow">➔</span>
                </div>
              )}
            </React.Fragment>
          ))}
        </div>
      </div>
    </section>
  );
};

export default HowItWorksSection;
