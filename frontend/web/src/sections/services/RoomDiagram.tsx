import React from "react";
import SectionHeading from "../../components/SectionHeading";
import Card from "../../components/Card";

export const RoomDiagram: React.FC = () => {
  return (
    <section className="room-diagram-section section-padding">
      <div className="container">
        <SectionHeading
          title="Gromit 통합 아키텍처 구조도"
          subtitle="메인룸, AI 백엔드, 백룸 간의 초저지연 연동 흐름을 직관적으로 구조화한 다이어그램입니다."
        />

        <Card variant="flat" padding="lg" className="diagram-card">
          <div className="diagram-svg-wrapper">
            <svg width="100%" height="320" viewBox="0 0 800 320" className="responsive-diagram-svg">
              <defs>
                <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--color-accent)" />
                </marker>
                <marker id="arrow-muted" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#86868b" />
                </marker>
                <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
                  <feDropShadow dx="0" dy="4" stdDeviation="6" floodOpacity="0.06" />
                </filter>
              </defs>

              {/* Node 1: Main Room */}
              <g transform="translate(40, 90)" filter="url(#shadow)">
                <rect width="180" height="120" rx="12" fill="#ffffff" stroke="var(--color-border)" strokeWidth="1" />
                <rect width="180" height="30" rx="12" fill="var(--color-surface)" />
                <rect x="0" y="20" width="180" height="10" fill="var(--color-surface)" />
                <text x="90" y="20" textAnchor="middle" fontSize="12" fontWeight="bold" fill="var(--color-text)">메인룸 (인터뷰 룸)</text>
                
                <text x="90" y="60" textAnchor="middle" fontSize="11" fill="var(--color-text-muted)">• 응답자 (음성 답변)</text>
                <text x="90" y="85" textAnchor="middle" fontSize="11" fill="var(--color-text-muted)">• AI 모더레이터 아바타</text>
              </g>

              {/* Node 2: Backend Core */}
              <g transform="translate(310, 90)" filter="url(#shadow)">
                <rect width="180" height="120" rx="12" fill="#ffffff" stroke="var(--color-accent)" strokeWidth="1.5" />
                <rect width="180" height="30" rx="12" fill="rgba(0, 102, 204, 0.05)" />
                <rect x="0" y="20" width="180" height="10" fill="rgba(0, 102, 204, 0.05)" />
                <text x="90" y="20" textAnchor="middle" fontSize="12" fontWeight="bold" fill="var(--color-accent)">AI 백엔드 코어</text>
                
                <text x="90" y="60" textAnchor="middle" fontSize="11" fill="var(--color-text-muted)">• 실시간 음성인식 / VAD</text>
                <text x="90" y="80" textAnchor="middle" fontSize="11" fill="var(--color-text-muted)">• 통역 에이전트 모듈</text>
                <text x="90" y="100" textAnchor="middle" fontSize="11" fill="var(--color-text-muted)">• 대화 턴 통제 모듈</text>
              </g>

              {/* Node 3: Back Room */}
              <g transform="translate(580, 90)" filter="url(#shadow)">
                <rect width="180" height="120" rx="12" fill="#ffffff" stroke="var(--color-border)" strokeWidth="1" />
                <rect width="180" height="30" rx="12" fill="var(--color-surface)" />
                <rect x="0" y="20" width="180" height="10" fill="var(--color-surface)" />
                <text x="90" y="20" textAnchor="middle" fontSize="12" fontWeight="bold" fill="var(--color-text)">백룸 (참관 콘솔)</text>
                
                <text x="90" y="60" textAnchor="middle" fontSize="11" fill="var(--color-text-muted)">• PM / 실시간 질문 개입</text>
                <text x="90" y="85" textAnchor="middle" fontSize="11" fill="var(--color-text-muted)">• 클라이언트 실시간 참관</text>
              </g>

              {/* Arrows & Flows */}
              {/* Flow 1: Left -> Center (Audio & Speech data) */}
              <path d="M 220,130 L 300,130" fill="none" stroke="var(--color-accent)" strokeWidth="1.5" marker-end="url(#arrow)" strokeDasharray="4 4" />
              <text x="260" y="120" textAnchor="middle" fontSize="9" fill="var(--color-accent)" fontWeight="bold">음성 스트림</text>

              {/* Flow 2: Center -> Left (Avartar control & feedback) */}
              <path d="M 300,170 L 230,170" fill="none" stroke="#86868b" strokeWidth="1.5" marker-end="url(#arrow-muted)" />
              <text x="265" y="190" textAnchor="middle" fontSize="9" fill="#86868b">AI 피드백</text>

              {/* Flow 3: Center -> Right (Translated transcript stream) */}
              <path d="M 490,130 L 570,130" fill="none" stroke="var(--color-accent)" strokeWidth="1.5" marker-end="url(#arrow)" strokeDasharray="4 4" />
              <text x="530" y="120" textAnchor="middle" fontSize="9" fill="var(--color-accent)" fontWeight="bold">번역 자막 스트림</text>

              {/* Flow 4: Right -> Center (Intervention inputs) */}
              <path d="M 580,170 L 500,170" fill="none" stroke="#86868b" strokeWidth="1.5" marker-end="url(#arrow-muted)" />
              <text x="540" y="190" textAnchor="middle" fontSize="9" fill="#86868b">질문 개입 지시</text>
            </svg>
          </div>
        </Card>
      </div>
    </section>
  );
};

export default RoomDiagram;
