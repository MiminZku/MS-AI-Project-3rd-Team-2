import React from "react";

interface StatBlockProps {
  value: string;
  label: string;
  description?: string;
  className?: string;
}

export const StatBlock: React.FC<StatBlockProps> = ({
  value,
  label,
  description,
  className = "",
}) => {
  return (
    <div className={`stat-block ${className}`}>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      {description && <div className="stat-description">{description}</div>}
    </div>
  );
};

export default StatBlock;
