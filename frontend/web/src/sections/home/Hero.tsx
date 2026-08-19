import React from "react";
import Button from "../../components/Button";

export const Hero: React.FC = () => {
  return (
    <section className="hero-section section-padding section--dark">
      <div className="container hero-container-centered">
        <div className="hero-content">
          <h1 className="hero-title">
            AI가 진행하고,<br />
            사람이 개입하는 정성조사
          </h1>
          <p className="hero-subtitle">
            기존 정성조사의 일정 조율과 인적 비용을 AI로 줄이되,<br />
            언제든 사람이 개입할 수 있는 실제 인터뷰 룸 환경
          </p>
          <div className="hero-actions">
            <Button variant="primary" size="lg" to="/services">
              서비스 살펴보기
            </Button>
            <Button variant="secondary" size="lg" to="/login">
              로그인
            </Button>
          </div>
        </div>

        <div className="hero-preview-centered">
          {/* Browser mockup frame */}
          <div className="mock-window">
            <div className="mock-window-header">
              <span className="dot dot-red"></span>
              <span className="dot dot-yellow"></span>
              <span className="dot dot-green"></span>
              <span className="window-title">Gromit Interview Room (Demo)</span>
            </div>
            <div className="mock-window-body">
              {/* Mainroom mockup layout */}
              <div className="mock-room-layout">
                {/* Left pane: AI Interviewer Avatar & Speech bubble */}
                <div className="mock-avatar-pane">
                  <div className="mock-avatar-sphere">
                    <span className="pulse-ring"></span>
                    <span className="pulse-ring-slow"></span>
                    <span className="logo-icon">G</span>
                  </div>
                  <div className="mock-avatar-label">AI Moderator</div>
                  <div className="mock-caption-box">
                    "오늘 인터뷰에서 가장 중요하게 생각하시는 가치에 대해 편하게 말씀해 주시겠어요?"
                  </div>
                </div>

                {/* Right pane: Respondent Camera Feed & Script info */}
                <div className="mock-respondent-pane">
                  <div className="mock-camera-feed">
                    <div className="mock-video-initial">Respondent</div>
                    <div className="mock-rec-indicator">
                      <span className="rec-dot"></span> LIVE
                    </div>
                  </div>
                  <div className="mock-live-stt">
                    <span className="stt-label">STT 실시간 번역</span>
                    <p>네, 저는 일정 조율 문제를 겪으면서 가장 크게...</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;
