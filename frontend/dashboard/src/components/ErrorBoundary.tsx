import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error in Dashboard:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "80vh",
          padding: "24px",
          color: "#e2e8f0",
          textAlign: "center"
        }}>
          <h2 style={{ fontSize: "20px", color: "#f87171", marginBottom: "12px" }}>
            화면을 불러오는 중 오류가 발생했습니다.
          </h2>
          <p style={{ fontSize: "14px", color: "#94a3b8", maxWidth: "480px", marginBottom: "20px" }}>
            {this.state.error?.message || "일시적인 렌더링 오류입니다. 페이지를 새로고침하거나 세션 목록으로 돌아가 주세요."}
          </p>
          <div style={{ display: "flex", gap: "12px" }}>
            <button
              style={{
                padding: "8px 16px",
                background: "#3b82f6",
                border: "none",
                borderRadius: "6px",
                color: "#ffffff",
                fontWeight: 600,
                cursor: "pointer"
              }}
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.href = "/dashboard/";
              }}
            >
              대시보드 처음으로 이동
            </button>
            <button
              style={{
                padding: "8px 16px",
                background: "rgba(255,255,255,0.1)",
                border: "1px solid rgba(255,255,255,0.2)",
                borderRadius: "6px",
                color: "#e2e8f0",
                cursor: "pointer"
              }}
              onClick={() => window.location.reload()}
            >
              새로고침
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
