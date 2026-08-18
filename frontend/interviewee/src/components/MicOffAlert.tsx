interface MicOffAlertProps {
  isVisible: boolean;
}

export default function MicOffAlert({ isVisible }: MicOffAlertProps) {
  if (!isVisible) return null;

  return (
    <div className="error-alert mic-off-alert" role="status">
      🎤 마이크가 꺼져 있어요 — 답변하려면 마이크 버튼을 눌러주세요
    </div>
  );
}
