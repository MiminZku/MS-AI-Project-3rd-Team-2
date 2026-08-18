import Orb from "./Orb";

interface AvatarMonitorProps {
  orbState: "idle" | "speaking" | "listening";
}

export default function AvatarMonitor({ orbState }: AvatarMonitorProps) {
  return (
    <section className="monitor monitor-avatar">
      <span className="monitor-tag">AI 모더레이터</span>
      <Orb status={orbState} />
    </section>
  );
}
