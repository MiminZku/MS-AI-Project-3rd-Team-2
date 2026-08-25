import type { MouseEvent } from "react";

interface InterviewHelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const helpSections = [
  {
    title: "아바타가 보이지 않아요",
    items: [
      "잠시 기다려 주세요. 네트워크 상태에 따라 로딩에 시간이 걸릴 수 있습니다.",
      "계속 보이지 않는 경우 화면의 새로고침 기능을 이용해 주세요.",
      "새로고침 이후에도 문제가 지속되면 인터뷰에 다시 입장해 주세요.",
    ],
  },
  {
    title: "화면이나 아바타가 끊겨요",
    items: [
      "다른 다운로드나 영상 재생을 잠시 중단해 주세요.",
      "인터넷 연결 상태를 확인해 주세요.",
      "잠시 기다려도 정상화되지 않으면 화면을 새로고침해 주세요.",
    ],
  },
  {
    title: "음성이 들리지 않아요",
    items: [
      "PC 또는 브라우저의 음량이 켜져 있는지 확인해 주세요.",
      "브라우저에서 오디오 재생이 차단되어 있지 않은지 확인해 주세요.",
      "사용할 수 있다면 이어폰 또는 스피커 연결 상태도 확인해 주세요.",
    ],
  },
  {
    title: "내 목소리가 인식되지 않아요",
    items: [
      "브라우저의 마이크 권한이 허용되어 있는지 확인해 주세요.",
      "사용 중인 마이크가 올바르게 선택되어 있는지 확인해 주세요.",
      "마이크를 사용하는 다른 프로그램이 있다면 종료 후 다시 시도해 주세요.",
    ],
  },
];

export default function InterviewHelpModal({ isOpen, onClose }: InterviewHelpModalProps) {
  if (!isOpen) return null;

  const closeOnBackdrop = (event: MouseEvent<HTMLDivElement>) => {
    if (event.target === event.currentTarget) onClose();
  };

  return (
    <div className="modal-overlay interview-help-overlay" role="presentation" onClick={closeOnBackdrop}>
      <section className="modal-content glass-panel interview-help-dialog" role="dialog" aria-modal="true" aria-labelledby="interview-help-title">
        <header className="interview-help-header">
          <h2 id="interview-help-title">인터뷰 이용 안내</h2>
          <button className="interview-help-close" type="button" aria-label="이용 안내 닫기" onClick={onClose}>×</button>
        </header>
        <div className="interview-help-content">
          {helpSections.map((section) => (
            <section key={section.title}>
              <h3>{section.title}</h3>
              <ul>
                {section.items.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </section>
          ))}
        </div>
        <button className="btn-primary interview-help-confirm" type="button" onClick={onClose}>확인</button>
      </section>
    </div>
  );
}
