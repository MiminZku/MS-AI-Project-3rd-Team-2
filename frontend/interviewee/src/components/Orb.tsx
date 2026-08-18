interface OrbProps {
  status: "idle" | "speaking" | "listening";
}

export default function Orb({ status }: OrbProps) {
  return (
    <div className={`orb-wrapper ${status}`}>
      <div className="orb-core" />
      <div className="orb-wave wave-1" />
      <div className="orb-wave wave-2" />
      <div className="orb-glow" />
    </div>
  );
}
