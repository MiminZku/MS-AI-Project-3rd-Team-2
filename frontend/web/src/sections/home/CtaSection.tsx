import React from "react";
import Button from "../../components/Button";

export const CtaSection: React.FC = () => {
  return (
    <section className="cta-section section-padding section--dark">
      <div className="container">
        <div className="cta-banner-card">
          <h2 className="cta-title">지금 바로 Gromit 솔루션을 만나보세요</h2>
          <p className="cta-description">
            정성조사의 일정 수립 한계와 과도한 조율 예산을 혁신적으로 절감해 드립니다.<br />
            데모 체험 및 솔루션 도입에 대한 문의를 남겨주시면 빠르게 답변해 드리겠습니다.
          </p>
          <div className="cta-button-wrapper">
            <Button variant="primary" size="lg" to="/contact">
              도입 문의
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
};

export default CtaSection;
