import React from "react";
import { NavLink } from "react-router-dom";

interface NavProps {
  vertical?: boolean;
  onLinkClick?: () => void;
}

export const Nav: React.FC<NavProps> = ({ vertical = false, onLinkClick }) => {
  const listClass = vertical ? "nav-list nav-list-vertical" : "nav-list";

  return (
    <nav className="nav-container">
      <ul className={listClass}>
        <li>
          <NavLink
            to="/"
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            onClick={onLinkClick}
          >
            Home
          </NavLink>
        </li>
        <li>
          <NavLink
            to="/about"
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            onClick={onLinkClick}
          >
            About
          </NavLink>
        </li>
        <li>
          <NavLink
            to="/services"
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            onClick={onLinkClick}
          >
            Services
          </NavLink>
        </li>
        <li>
          <NavLink
            to="/team"
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            onClick={onLinkClick}
          >
            Team
          </NavLink>
        </li>
        <li>
          <NavLink
            to="/contact"
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            onClick={onLinkClick}
          >
            Contact
          </NavLink>
        </li>
      </ul>
    </nav>
  );
};

export default Nav;
