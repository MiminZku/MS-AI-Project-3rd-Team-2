import React, { useState } from "react";
import PageHeader from "../components/PageHeader";
import Card from "../components/Card";
import Button from "../components/Button";

export const Contact: React.FC = () => {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    company: "",
    message: "",
  });
  const [showNotice, setShowNotice] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // 전송 로직은 구현하지 않는다. 제출 시 안내만 표시.
    setShowNotice(true);
    // 3초 뒤 안내 닫기
    setTimeout(() => setShowNotice(false), 4000);
  };

  return (
    <div className="contact-page">
      <PageHeader
        title="Contact"
        description="Gromit 서비스 도입 및 데모 신청 문의를 남겨주세요."
        className="section--dark"
      />

      <section className="contact-section-content section-padding">
        <div className="container contact-grid">
          {/* Inquiry Form */}
          <div className="contact-form-pane">
            <Card variant="default" padding="lg">
              <h3 className="contact-pane-title">도입 및 문의 신청</h3>
              <form onSubmit={handleSubmit} className="inquiry-form">
                <div className="form-group">
                  <label htmlFor="inquiry-name">이름</label>
                  <input
                    type="text"
                    id="inquiry-name"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="홍길동"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="inquiry-email">이메일</label>
                  <input
                    type="email"
                    id="inquiry-email"
                    required
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder="example@gromit.ai"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="inquiry-company">회사/소속</label>
                  <input
                    type="text"
                    id="inquiry-company"
                    required
                    value={formData.company}
                    onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                    placeholder="Gromit AI"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="inquiry-message">문의내용</label>
                  <textarea
                    id="inquiry-message"
                    rows={5}
                    required
                    value={formData.message}
                    onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                    placeholder="문의하실 내용을 입력해 주세요."
                  />
                </div>

                <Button variant="primary" size="md" type="submit" className="contact-submit-btn">
                  문의 제출하기
                </Button>
              </form>

              {showNotice && (
                <div className="form-notice-banner">
                  💡 데모 환경입니다. 입력하신 문의는 전송되지 않습니다.
                </div>
              )}
            </Card>
          </div>

          {/* Info & Map Pane */}
          <div className="contact-info-pane">
            <Card variant="flat" padding="lg" className="info-details-card">
              <h3 className="contact-pane-title">회사 연락 정보</h3>
              
              <div className="info-item">
                <span className="info-icon">✉</span>
                <div className="info-text-group">
                  <span className="info-label">이메일 문의</span>
                  {/* contactus@gromit.ai - 자료:리소스 고지문 기준 [확인 필요] 임시 값 */}
                  <a href="mailto:contactus@gromit.ai" className="info-value">
                    contactus@gromit.ai
                  </a>
                  <span className="temp-badge">[확인 필요 - 임시]</span>
                </div>
              </div>

              <div className="info-item info-item-map">
                <span className="info-icon">📍</span>
                <div className="info-text-group info-map-wrapper">
                  <span className="info-label">찾아오시는 길</span>
                  {/* 위치: 아직 확정된 주소 없음 → 지도 임베드 대신 "위치 정보 준비 중" 플레이스홀더 */}
                  <div className="map-placeholder">
                    <span className="placeholder-text">위치 정보 준비 중</span>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Contact;
