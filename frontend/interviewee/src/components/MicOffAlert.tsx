interface MicOffAlertProps {
  isVisible: boolean;
}

export default function MicOffAlert({ isVisible }: MicOffAlertProps) {
  if (!isVisible) return null;

  return (
    <div className="error-alert" style={{ textAlign: "center", margin: "16px 0", animation: "smoothFadeUp 0.3s ease-out" }}>
      🎤 마이크가 꺼져 있어요 — 답변하려면 마이크 버튼을 눌러주세요
    </div>
  );
}
