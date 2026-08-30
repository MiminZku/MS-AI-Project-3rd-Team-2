import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowUpRight, ChartDonut, ShieldCheck, UsersThree } from "@phosphor-icons/react";
import { useRole, type UserRole } from "../auth/RoleContext";
import Button from "../components/Button";

const roleCopy: Record<UserRole, { description: string; emailLabel: string; passwordLabel: string; submitLabel: string }> = {
  pm: {
    description: "프로젝트 관리 대시보드 및 현장 운영을 위해 접속합니다.",
    emailLabel: "이메일",
    passwordLabel: "비밀번호",
    submitLabel: "PM 대시보드 입장",
  },
  client: {
    description: "PM이 전달한 Project Access ID로 하나의 조사 결과만 확인합니다.",
    emailLabel: "회사 이메일",
    passwordLabel: "접근 비밀번호",
    submitLabel: "Project Access ID 입력",
  },
};

export default function Login() {
  const [activeRole, setActiveRole] = useState<UserRole>("pm");
  const { login } = useRole();
  const navigate = useNavigate();
  const selectedRole = roleCopy[activeRole];

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    login(activeRole);
    navigate(activeRole === "client" ? "/client/access" : "/projects");
  };

  return (
    <main className="login-page">
      <section className="login-section-content">
        <div className="container login-layout">
          <aside className="login-brand-panel" aria-label="Gromit Research Workspace 소개">
            <Link className="login-wordmark" to="/">Gromit <ArrowUpRight size={17} weight="bold" /></Link>
            <div className="login-brand-copy">
              <p className="login-product-label">RESEARCH WORKSPACE</p>
              <h1>조사의 모든 순간을<br /><em>한 곳에서.</em></h1>
              <p>가이드라인부터 인터뷰 운영, 근거 기반 결과와 다운로드까지. 팀의 의사결정을 위한 조사 흐름을 연결합니다.</p>
            </div>
            <div className="login-brand-signals" aria-label="Gromit workspace capabilities">
              <div><ChartDonut size={21} weight="duotone" /><span><strong>Evidence first</strong>결과의 근거를 바로 확인</span></div>
              <div><UsersThree size={21} weight="duotone" /><span><strong>Role-aware access</strong>PM과 클라이언트의 화면 분리</span></div>
              <div><ShieldCheck size={21} weight="duotone" /><span><strong>Controlled delivery</strong>권한에 맞는 산출물 제공</span></div>
            </div>
          </aside>

          <section className="login-auth-panel" aria-labelledby="login-title">
            <header className="login-heading">
              <p className="login-product-label">SIGN IN</p>
              <h2 id="login-title">참관자 대시보드 로그인</h2>
              <p className="login-intro">{selectedRole.description}</p>
            </header>

            <form onSubmit={handleSubmit} className="login-form login-card">
              <div className="login-tab-container" aria-label="워크스페이스 역할 선택">
                <button
                  aria-pressed={activeRole === "pm"}
                  className={`login-tab-btn ${activeRole === "pm" ? "active" : ""}`}
                  onClick={() => setActiveRole("pm")}
                  type="button"
                >
                  PM 로그인
                </button>
                <button
                  aria-pressed={activeRole === "client"}
                  className={`login-tab-btn ${activeRole === "client" ? "active" : ""}`}
                  onClick={() => setActiveRole("client")}
                  type="button"
                >
                  클라이언트 로그인
                </button>
              </div>

              {activeRole === "pm" ? (
                <div className="login-credentials">
                  <label className="login-field">
                    <span>{selectedRole.emailLabel}</span>
                    <input autoComplete="email" name="email" placeholder="name@company.com" type="email" />
                  </label>
                  <label className="login-field">
                    <span>{selectedRole.passwordLabel}</span>
                    <input autoComplete="current-password" name="password" placeholder="비밀번호를 입력하세요" type="password" />
                  </label>
                </div>
              ) : (
                <div className="login-client-route-note">
                  <KeyRoundIcon />
                  <span>다음 화면에서 PM에게 전달받은 Project Access ID를 입력합니다.</span>
                </div>
              )}

              <Button className="login-submit-btn" size="md" type="submit" variant="primary">
                {selectedRole.submitLabel}
              </Button>
            </form>
            <Link className="login-client-access-link" to="/client/access">
              Client 초대 링크가 있으신가요? <strong>Project Access ID로 접속</strong>
            </Link>
            <p className="login-support">접근 권한이 없거나 초대 메일을 찾을 수 없나요? <a href="mailto:research@gromit.team">Research 운영팀에 문의</a></p>
          </section>
        </div>
      </section>
    </main>
  );
}

function KeyRoundIcon() {
  return <ShieldCheck size={20} weight="duotone" aria-hidden="true" />;
}
