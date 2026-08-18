import Orb from "./Orb";

interface AvatarMonitorProps {
  orbState: "idle" | "speaking" | "listening";
  question: string;
}

export default function AvatarMonitor({ orbState, question }: AvatarMonitorProps) {
  return (
    <section className="monitor monitor-avatar">
      <span className="monitor-tag">AI 모더레이터</span>
      <Orb status={orbState} />
      <div className="question-box">
        <p className="question-bubble">{question}</p>
      </div>
    </section>
  );
}
