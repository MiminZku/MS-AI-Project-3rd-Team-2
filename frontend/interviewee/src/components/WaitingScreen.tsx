interface WaitingScreenProps {
  title: string;
}

export default function WaitingScreen({ title }: WaitingScreenProps) {
  return (
    <section className="waiting-screen glass-panel">
      <div className="avatar-pulse-container">
        <div className="pulse-avatar" />
        <div className="pulse-ring ring-1" />
        <div className="pulse-ring ring-2" />
      </div>
      <h2>대기 중...</h2>
      <p className="session-title">『 {title || "AI 인터뷰"} 』</p>
      <p className="muted">
        면접관(PM)이 인터뷰를 시작할 때까지 잠시만 기다려 주세요.<br />
        시작 시 화면이 자동으로 전환됩니다.
      </p>
    </section>
  );
}
