import { CaretDown, ChartBar, DownloadSimple, FileArrowUp, Headphones, SquaresFour } from "@phosphor-icons/react";
import React from "react";
import { NavLink } from "react-router-dom";
import { useRole } from "../auth/RoleContext";

interface NavProps {
  vertical?: boolean;
  onLinkClick?: () => void;
}

export const Nav: React.FC<NavProps> = ({ vertical = false, onLinkClick }) => {
  const { role } = useRole();
  const listClass = vertical ? "nav-list nav-list-vertical" : "nav-list";

  if (vertical) {
    return (
      <nav className="nav-container" aria-label="모바일 주 메뉴">
        <ul className={listClass}>
          <li className="nav-mobile-label">제품</li>
          <li><NavLink to="/projects" className="nav-link" onClick={onLinkClick}>Research Workspace</NavLink></li>
          <li><NavLink to="/projects" className="nav-link" onClick={onLinkClick}>가이드 업로드</NavLink></li>
          {role === "pm" ? <li><NavLink to="/services" className="nav-link" onClick={onLinkClick}>인터뷰와 참관</NavLink></li> : null}
          <li><NavLink to="/projects" className="nav-link" onClick={onLinkClick}>Research Results</NavLink></li>
          <li><NavLink to="/downloads" className="nav-link" onClick={onLinkClick}>다운로드 센터</NavLink></li>
          <li className="nav-mobile-divider" />
          <li><NavLink to="/about" className="nav-link" onClick={onLinkClick}>작동 방식</NavLink></li>
          <li><NavLink to="/contact" className="nav-link" onClick={onLinkClick}>문의하기</NavLink></li>
        </ul>
      </nav>
    );
  }

  return (
    <nav className="nav-container" aria-label="주 메뉴">
      <ul className={listClass}>
        <li className="product-menu">
          <NavLink to="/projects" className={({ isActive }) => (isActive ? "nav-link active product-menu__trigger" : "nav-link product-menu__trigger")} onClick={onLinkClick}>
            제품 <CaretDown size={14} weight="bold" aria-hidden="true" />
          </NavLink>
          <div className="product-menu__panel">
            <span className="product-menu__eyebrow">Product</span>
            <NavLink to="/projects" onClick={onLinkClick}><span><SquaresFour size={18} weight="duotone" /></span><b>Research Workspace<small>프로젝트와 세션을 관리합니다</small></b></NavLink>
            <NavLink to="/projects" onClick={onLinkClick}><span><FileArrowUp size={18} weight="duotone" /></span><b>가이드 업로드<small>문서에서 질문 구조를 만듭니다</small></b></NavLink>
            {role === "pm" ? <NavLink to="/services" onClick={onLinkClick}><span><Headphones size={18} weight="duotone" /></span><b>인터뷰와 참관<small>대화와 진행 상태를 확인합니다</small></b></NavLink> : null}
            <NavLink to="/projects" onClick={onLinkClick}><span><ChartBar size={18} weight="duotone" /></span><b>Research Results<small>시각화와 산출물을 확인합니다</small></b></NavLink>
            <NavLink to="/downloads" onClick={onLinkClick}><span><DownloadSimple size={18} weight="duotone" /></span><b>다운로드 센터<small>리포트와 분석 파일을 받습니다</small></b></NavLink>
          </div>
        </li>
        <li>
          <NavLink
            to="/projects"
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            onClick={onLinkClick}
          >
            프로젝트
          </NavLink>
        </li>
        <li>
          <NavLink
            to="/projects"
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            onClick={onLinkClick}
          >
            리포트
          </NavLink>
        </li>
        <li>
          <NavLink
            to="/about"
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            onClick={onLinkClick}
          >
            작동 방식
          </NavLink>
        </li>
        <li>
          <NavLink
            to="/downloads"
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            onClick={onLinkClick}
          >
            다운로드
          </NavLink>
        </li>
      </ul>
    </nav>
  );
};

export default Nav;
