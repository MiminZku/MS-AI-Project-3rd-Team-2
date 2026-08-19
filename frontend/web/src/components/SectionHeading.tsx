import React from "react";

interface SectionHeadingProps {
  title: string;
  subtitle?: string;
  align?: "left" | "center" | "right";
  className?: string;
}

export const SectionHeading: React.FC<SectionHeadingProps> = ({
  title,
  subtitle,
  align = "left",
  className = "",
}) => {
  const classNames = `section-heading section-heading-${align} ${className}`;
  return (
    <div className={classNames}>
      <h2 className="section-heading-title">{title}</h2>
      {subtitle && <p className="section-heading-subtitle">{subtitle}</p>}
    </div>
  );
};

export default SectionHeading;
