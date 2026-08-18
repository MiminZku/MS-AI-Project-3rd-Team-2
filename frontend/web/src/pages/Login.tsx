import React, { useState } from "react";
import PageHeader from "../components/PageHeader";
import Card from "../components/Card";
import Button from "../components/Button";

export const Login: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"pm" | "client">("pm");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    
    // VITE_DASHBOARD_URL 은 import.meta.env 에서 읽고, 없을 경우 로컬 개발용 5174 포트 사용
    const dashboardBaseUrl = import.meta.env.VITE_DASHBOARD_URL || "http://localhost:5174";
    
    // 역할(role) 쿼리 스트링만 붙여 이동
    const redirectUrl = `${dashboardBaseUrl}?role=${activeTab}`;
    
    // 보안 규정 준수: 입력된 email, password 값을 localStorage, sessionStorage, URL 어디에도 저장하거나 전달하지 않고 즉시 이동
    window.location.href = redirectUrl;
  };

  return (
    <div className="login-page section--dark" style={{ minHeight: "calc(100vh - 64px - 280px)" }}>
      <PageHeader
        title="Gromit 포털 로그인"
        description="프로젝트 관리 대시보드 및 참관용 백룸에 접속합니다."
        className="section--dark"
      />

      <section className="login-section-content section-padding section--dark">
        <div className="container login-container-small">
          <Card variant="default" padding="lg" className="login-card">
            
            {/* Demo Environment Banner */}
            <div className="demo-notice-banner">
              ⚠️ 현재 데모 환경으로, 인증 없이 대시보드로 이동합니다.
            </div>

            {/* Role Selection Tabs */}
            <div className="login-tab-container">
              <button
                type="button"
                className={`login-tab-btn ${activeTab === "pm" ? "active" : ""}`}
                onClick={() => {
                  setActiveTab("pm");
                  setEmail("");
                  setPassword("");
                }}
              >
                PM 로그인
              </button>
              <button
                type="button"
                className={`login-tab-btn ${activeTab === "client" ? "active" : ""}`}
                onClick={() => {
                  setActiveTab("client");
                  setEmail("");
                  setPassword("");
                }}
              >
                클라이언트 로그인
              </button>
            </div>

            {/* Tab Description */}
            <div className="login-role-description">
              {activeTab === "pm" 
                ? "세션 생성, 질문 편집, AI 진행자에게 실시간 지시가 가능합니다"
                : "인터뷰를 실시간 참관할 수 있습니다. 질문 개입은 PM을 통해 요청해 주세요"
              }
            </div>

            {/* Login Form */}
            <form onSubmit={handleLogin} className="login-form">
              <div className="form-group">
                <label htmlFor="login-email">이메일 주소</label>
                <input
                  type="email"
                  id="login-email"
                  placeholder="name@gromit.ai"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="login-password">비밀번호</label>
                <input
                  type="password"
                  id="login-password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>

              <Button variant="primary" size="md" type="submit" className="login-submit-btn">
                {activeTab === "pm" ? "PM 대시보드 입장" : "참관룸 입장"}
              </Button>
            </form>
          </Card>
        </div>
      </section>
    </div>
  );
};

export default Login;
