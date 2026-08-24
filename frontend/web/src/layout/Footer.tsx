import React from "react";
import { Link } from "react-router-dom";
import { useRole } from "../auth/RoleContext";

export const Footer: React.FC = () => {
  const { role } = useRole();
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
            의사결정에 필요한 사람의 목소리를<br />
            한 화면으로 연결하는 리서치 플랫폼
          </p>
        </div>

        <div className="footer-links-grid">
          <div className="footer-links-column">
            <h4 className="footer-column-title">제품</h4>
            <ul>
              <li><Link to="/projects">Research Workspace</Link></li>
              {role === "pm" ? <li><Link to="/services">인터뷰와 참관</Link></li> : null}
              <li><Link to="/projects">Research Results</Link></li>
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
            <h4 className="footer-column-title">산출물</h4>
            <ul>
              <li><Link to="/downloads">다운로드 센터</Link></li>
              <li><Link to="/downloads">Word 리포트</Link></li>
              {role === "pm" ? <li><Link to="/downloads">Power BI 데이터</Link></li> : null}
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
