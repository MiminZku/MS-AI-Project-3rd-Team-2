import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import Nav from "./Nav";
import Button from "../components/Button";

export const Header: React.FC = () => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const navigate = useNavigate();

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

  const handleLoginClick = () => {
    setIsMobileMenuOpen(false);
    navigate("/login");
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
          <Button variant="primary" size="sm" to="/login">
            로그인
          </Button>
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
              <Button variant="primary" size="lg" onClick={handleLoginClick} style={{ width: "100%" }}>
                로그인
              </Button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
