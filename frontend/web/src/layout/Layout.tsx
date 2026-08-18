import React from "react";
import { Outlet } from "react-router-dom";
import Header from "./Header";
import Footer from "./Footer";

export const Layout: React.FC = () => {
  return (
    <div className="site-layout">
      <Header />
      <div className="layout-content">
        <Outlet />
      </div>
      <Footer />
    </div>
  );
};

export default Layout;
