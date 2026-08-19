import React from "react";
import { Link } from "react-router-dom";

export const Footer: React.FC = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="site-footer">
      <div className="container footer-container">
        <div className="footer-brand">
          <Link to="/" className="footer-logo">
            <span className="logo-icon">G</span>
            <span className="logo-text">Gromit</span>
          </Link>
          <p className="footer-tagline">
            AI가 진행하고, 사람이 개입하는<br />
            차세대 정성조사 플랫폼
          </p>
        </div>

        <div className="footer-links-grid">
          <div className="footer-links-column">
            <h4 className="footer-column-title">서비스</h4>
            <ul>
              <li><Link to="/services">정성 인터뷰</Link></li>
              <li><Link to="/services">조사 리포트 분석</Link></li>
              <li><Link to="/services">최종 산출물</Link></li>
            </ul>
          </div>

          <div className="footer-links-column">
            <h4 className="footer-column-title">회사</h4>
            <ul>
              <li><Link to="/about">About Us</Link></li>
              <li><Link to="/team">우리 팀원</Link></li>
              <li><Link to="/contact">문의하기</Link></li>
            </ul>
          </div>

          <div className="footer-links-column">
            <h4 className="footer-column-title">법적고지</h4>
            <ul>
              <li><a href="#privacy">개인정보처리방침</a></li>
              <li><a href="#terms">이용약관</a></li>
            </ul>
          </div>
        </div>
      </div>

      <div className="container footer-bottom">
        <div className="footer-contact">
          <span>이메일 문의:</span>{" "}
          <a href="mailto:contactus@gromit.ai" className="footer-email">
            contactus@gromit.ai
          </a>
        </div>
        <div className="footer-copyright">
          &copy; {currentYear} Gromit. All rights reserved.
        </div>
      </div>
    </footer>
  );
};

export default Footer;
