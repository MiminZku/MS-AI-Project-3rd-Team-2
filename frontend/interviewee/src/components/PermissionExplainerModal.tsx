interface PermissionExplainerModalProps {
  isOpen: boolean;
  onConfirm: () => void;
}

export default function PermissionExplainerModal({
  isOpen,
  onConfirm,
}: PermissionExplainerModalProps) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content glass-panel text-center">
        <h2 style={{ color: "var(--text-white)", marginTop: 0 }}>🎥 장치 권한 안내</h2>
        <p className="muted" style={{ marginBottom: 24, fontSize: "15px", lineHeight: "1.6" }}>
          잠시 후 브라우저가 마이크와 카메라 권한을 요청합니다.<br />
          원활한 인터뷰 진행을 위해 <strong>허용</strong>을 눌러주시기 바랍니다.
        </p>
        <button className="btn-primary" onClick={onConfirm}>
          확인
        </button>
      </div>
    </div>
  );
}
