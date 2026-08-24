import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import Nav from "./Nav";
import Button from "../components/Button";
import { useRole } from "../auth/RoleContext";

export const Header: React.FC = () => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const navigate = useNavigate();
  const { role, logout } = useRole();
  const isPm = role === "pm";
  const roleLabel = isPm ? "PM 운영" : "클라이언트 전달용";

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen((prev) => !prev);
  };

  // Prevent background scroll when mobile menu is active
  useEffect(() => {
    if (isMobileMenuOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isMobileMenuOpen]);

  const handlePrimaryAction = () => {
    setIsMobileMenuOpen(false);
    navigate(isPm ? "/projects" : "/downloads");
  };

  const handleLogout = () => {
    setIsMobileMenuOpen(false);
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <header className="site-header">
      <div className="container header-container">
        <Link to="/" className="site-logo" onClick={() => setIsMobileMenuOpen(false)}>
          <span className="logo-icon">G</span>
          <span className="logo-text">Gromit</span>
        </Link>

        {/* Desktop Navigation */}
        <div className="desktop-only header-nav-desktop">
          <Nav />
        </div>

        <div className="desktop-only header-actions-desktop">
          <span className={`header-role-badge header-role-badge--${isPm ? "pm" : "client"}`}>{roleLabel}</span>
          <Button variant="primary" size="sm" to={isPm ? "/projects" : "/downloads"}>
            {isPm ? "새 조사 만들기" : "전달 리포트"}
          </Button>
          <button type="button" className="header-logout" onClick={handleLogout} aria-label="로그아웃">로그아웃</button>
        </div>

        {/* Mobile Hamburger Button */}
        <button
          className="mobile-only burger-button"
          onClick={toggleMobileMenu}
          aria-label="메뉴 열기/닫기"
          aria-expanded={isMobileMenuOpen}
        >
          <span className="burger-bar"></span>
          <span className="burger-bar"></span>
          <span className="burger-bar"></span>
        </button>

        {/* Mobile Fullscreen Overlay Menu */}
        <div className={`mobile-menu-overlay ${isMobileMenuOpen ? "open" : ""}`}>
          <div className="mobile-menu-content">
            <Nav vertical onLinkClick={() => setIsMobileMenuOpen(false)} />
            <div className="mobile-menu-actions">
              <span className={`header-role-badge header-role-badge--${isPm ? "pm" : "client"}`}>{roleLabel}</span>
              <Button variant="primary" size="lg" onClick={handlePrimaryAction} style={{ width: "100%" }}>
                {isPm ? "새 조사 만들기" : "전달 리포트 보기"}
              </Button>
              <button type="button" className="header-logout header-logout--mobile" onClick={handleLogout} aria-label="로그아웃">로그아웃</button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
