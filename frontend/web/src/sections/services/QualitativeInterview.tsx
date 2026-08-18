import React from "react";
import SectionHeading from "../../components/SectionHeading";
import Card from "../../components/Card";

export const QualitativeInterview: React.FC = () => {
  return (
    <section className="qualitative-interview-section section-padding">
      <div className="container">
        <SectionHeading
          title="① 정성 인터뷰 솔루션"
          subtitle="Gromit의 정성 인터뷰 서비스는 메인룸, 백룸, 그리고 관찰자용 즉각적 개입 장치가 일련의 유기적인 모듈로 결합되어 설계되었습니다."
        />

        <div className="services-cards-grid">
          {/* Card A: Main Room */}
          <Card variant="interactive" padding="lg" className="service-feature-card">
            <div className="service-thumbnail">
              <svg width="100%" height="120" viewBox="0 0 200 120">
                <rect width="200" height="120" rx="8" fill="#1e1f29" />
                <circle cx="100" cy="50" r="24" fill="var(--color-accent)" />
                <text x="100" y="54" textAnchor="middle" fill="#fff" fontSize="12" fontWeight="bold">AI</text>
                <rect x="30" y="90" width="140" height="16" rx="4" fill="rgba(255,255,255,0.15)" />
                <text x="100" y="101" textAnchor="middle" fill="#fff" fontSize="8">"음성으로 답변해 주세요"</text>
              </svg>
            </div>
            <h3 className="feature-card-title">(a) 메인룸 (Main Room)</h3>
            <p className="feature-card-text">
              인터뷰이(응답자)가 대기 및 인터뷰를 갖는 본 공간입니다. 매력적인 AI 아바타 모더레이터가 가이드를 진행하며, 응답자는 기기 장벽 없이 오직 <strong>음성</strong>을 통해 즉각 답변할 수 있습니다.
            </p>
          </Card>

          {/* Card B: Back Room */}
          <Card variant="interactive" padding="lg" className="service-feature-card">
            <div className="service-thumbnail">
              <svg width="100%" height="120" viewBox="0 0 200 120">
                <rect width="200" height="120" rx="8" fill="#0d0e12" />
                <rect x="15" y="15" width="100" height="50" rx="4" fill="rgba(255,255,255,0.06)" stroke="rgba(255,255,255,0.15)" />
                <rect x="15" y="75" width="100" height="30" rx="4" fill="rgba(255,255,255,0.06)" stroke="rgba(255,255,255,0.15)" />
                <rect x="125" y="15" width="60" height="90" rx="4" fill="rgba(255,255,255,0.06)" stroke="rgba(255,255,255,0.15)" />
                <circle cx="65" cy="40" r="10" fill="#3a3a4a" />
                <line x1="25" y1="90" x2="105" y2="90" stroke="var(--color-accent)" strokeWidth="2" />
                <text x="155" y="60" textAnchor="middle" fill="rgba(255,255,255,0.4)" fontSize="8">AI 판단</text>
              </svg>
            </div>
            <h3 className="feature-card-title">(b) 백룸 (Back Room)</h3>
            <p className="feature-card-text">
              PM 및 클라이언트들이 로그인해 들어오는 실시간 참관룸입니다. 딜레이 없는 다국어 번역 자막을 확인하고 AI가 분석해 주는 답변 판단 근거를 실시간으로 모니터링할 수 있습니다.
            </p>
          </Card>

          {/* Card C: Real-time Intervention */}
          <Card variant="interactive" padding="lg" className="service-feature-card">
            <div className="service-thumbnail">
              <svg width="100%" height="120" viewBox="0 0 200 120">
                <rect width="200" height="120" rx="8" fill="#14151b" />
                <rect x="20" y="25" width="160" height="36" rx="6" fill="rgba(0, 102, 204, 0.1)" stroke="var(--color-accent)" />
                <text x="100" y="47" textAnchor="middle" fill="var(--color-accent)" fontSize="10" fontWeight="bold">지시 입력 및 개입</text>
                <path d="M100 70 L100 85 M95 80 L100 85 L105 80" fill="none" stroke="var(--color-accent)" strokeWidth="2" />
                <rect x="50" y="95" width="100" height="12" rx="3" fill="rgba(255,255,255,0.1)" />
              </svg>
            </div>
            <h3 className="feature-card-title">(c) 실시간 개입</h3>
            <p className="feature-card-text">
              모니터링 중인 PM이 백룸 콘솔창에 직접 추가 지시 사항이나 꼬리 질문을 입력하면, AI 모더레이터의 다음 차례 턴 진행 시점에 그 내용이 자동 조합 및 유기적으로 변환 반영됩니다.
            </p>
          </Card>
        </div>
      </div>
    </section>
  );
};

export default QualitativeInterview;
