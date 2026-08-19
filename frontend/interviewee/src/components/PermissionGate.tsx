import { useState } from "react";

interface PermissionGateProps {
  onConsentComplete: () => void;
}

export default function PermissionGate({ onConsentComplete }: PermissionGateProps) {
  const [hasMicPermission, setHasMicPermission] = useState<boolean | null>(null);
  const [hasCamPermission, setHasCamPermission] = useState<boolean | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const [isAgreedToRecord, setIsAgreedToRecord] = useState(false);
  const [isAgreedToPrivacy, setIsAgreedToPrivacy] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const checkPermissions = async () => {
    setIsChecking(true);
    setErrorMsg("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: true,
      });
      setHasMicPermission(true);
      setHasCamPermission(true);
      stream.getTracks().forEach((track) => track.stop());
    } catch (err: any) {
      console.error("Permission check failed:", err);
      setHasMicPermission(false);
      setHasCamPermission(false);
      setErrorMsg("카메라 및 마이크 권한을 허용해 주셔야 인터뷰 진행이 가능합니다.");
    } finally {
      setIsChecking(false);
    }
  };

  const handleStart = () => {
    if (!hasMicPermission || !hasCamPermission) {
      setErrorMsg("카메라와 마이크 권한 확인이 완료되어야 합니다.");
      return;
    }
    if (!isAgreedToRecord || !isAgreedToPrivacy) {
      setErrorMsg("모든 필수 약관에 동의해 주셔야 합니다.");
      return;
    }
    onConsentComplete();
  };

  return (
    <section className="permission-gate glass-panel">
      <h2>🎙️ 인터뷰 시작 전 안내 및 설정</h2>
      <p className="muted desc">
        본 인터뷰는 원활한 진행 및 평가 기록을 위해 오디오 녹음 및 비디오 녹화가 수행됩니다. 아래 항목들을 확인해 주세요.
      </p>

      <div className="check-block">
        <h3>1. 장치 권한 확인</h3>
        <p className="muted">마이크와 카메라가 정상적으로 연동되는지 테스트합니다.</p>
        <div className="device-status-row">
          <div className={`status-pill ${hasMicPermission ? "success" : "pending"}`}>
            마이크: {hasMicPermission === true ? "허용됨 ✅" : hasMicPermission === false ? "허용 안 됨 ❌" : "대기 중 ⏳"}
          </div>
          <div className={`status-pill ${hasCamPermission ? "success" : "pending"}`}>
            카메라: {hasCamPermission === true ? "허용됨 ✅" : hasCamPermission === false ? "허용 안 됨 ❌" : "대기 중 ⏳"}
          </div>
        </div>
        <button className="btn-secondary" onClick={checkPermissions} disabled={isChecking}>
          {isChecking ? "권한 확인 중..." : "장치 권한 테스트 및 요청"}
        </button>
      </div>

      <div className="agree-block">
        <h3>2. 녹화 고지 및 동의</h3>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={isAgreedToRecord}
            onChange={(e) => setIsAgreedToRecord(e.target.checked)}
          />
          <span>(필수) 인터뷰 내용 녹음 및 영상 녹화에 동의합니다.</span>
        </label>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={isAgreedToPrivacy}
            onChange={(e) => setIsAgreedToPrivacy(e.target.checked)}
          />
          <span>(필수) 개인정보 및 데이터 분석 활용에 동의합니다.</span>
        </label>
      </div>

      {errorMsg && <p className="error-alert">{errorMsg}</p>}

      <button
        className="btn-primary start-btn"
        onClick={handleStart}
        disabled={!hasMicPermission || !hasCamPermission || !isAgreedToRecord || !isAgreedToPrivacy}
      >
        인터뷰 룸 입장하기
      </button>
    </section>
  );
}
