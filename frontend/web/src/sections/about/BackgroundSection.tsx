import React, { useState } from "react";
import SectionHeading from "../../components/SectionHeading";

interface AccordionItemProps {
  title: string;
  content: string;
}

const AccordionItem: React.FC<AccordionItemProps> = ({ title, content }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className={`accordion-item ${isOpen ? "active" : ""}`}>
      <button 
        className="accordion-header" 
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
      >
        <span className="accordion-title">{title}</span>
        <span className="accordion-icon">{isOpen ? "−" : "+"}</span>
      </button>
      <div className={`accordion-collapse ${isOpen ? "open" : ""}`}>
        <div className="accordion-body">
          <p>{content}</p>
        </div>
      </div>
    </div>
  );
};

export const BackgroundSection: React.FC = () => {
  return (
    <section className="background-section section-padding">
      <div className="container">
        <SectionHeading
          title="정성조사 용어 사전 (FAQ)"
          subtitle="처음 방문하시거나 실무 용어가 생소하신 분들을 위해 준비했습니다. 탭을 클릭하여 각 상세 설명을 확인해 보세요."
        />

        <div className="accordion-container">
          <AccordionItem
            title="IDI (In-depth Interview, 일대일 심층 인터뷰)가 무엇인가요?"
            content="IDI는 전문 모더레이터(진행자)와 응답자가 1대1로 마주하여 특정 주제나 브랜드, 제품에 관해 깊이 있게 대화를 나누는 정성조사 기법입니다. 일반 설문조사에서는 얻기 힘든 소비자의 무의식적인 니즈, 숨겨진 태도와 구체적인 맥락을 관찰할 수 있습니다."
          />
          <AccordionItem
            title="백룸(참관룸)이 무엇인가요?"
            content="인터뷰가 실제로 진행되는 면접 환경(메인룸) 외부에서 프로젝트의 총괄 관리자(PM) 및 의뢰 회사(클라이언트)가 대화 및 관찰에 영향을 미치지 않고 실시간으로 조사 현장을 모니터링할 수 있도록 설계된 특별한 공간입니다."
          />
          <AccordionItem
            title="정성조사는 어떤 목적으로 수행하나요?"
            content="설문조사 등 정량조사가 '얼마나 많은지(수치)'를 측정한다면, 정성조사는 '왜 그러한지(이유와 태도)'를 파헤칩니다. 새로운 아이디어를 도출하고, 사용자 경험상의 핵심 Pain Point를 분석하며, 신제품 출시에 앞서 정성적 피드백을 모으는 데 매우 적합합니다."
          />
        </div>
      </div>
    </section>
  );
};

export default BackgroundSection;
