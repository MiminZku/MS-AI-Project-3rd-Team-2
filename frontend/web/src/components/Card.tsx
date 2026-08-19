import React from "react";

interface CardProps {
  children: React.ReactNode;
  variant?: "default" | "flat" | "interactive";
  padding?: "none" | "sm" | "md" | "lg";
  className?: string;
}

export const Card: React.FC<CardProps> = ({
  children,
  variant = "default",
  padding = "md",
  className = "",
}) => {
  const classNames = `card card-${variant} card-pad-${padding} ${className}`;
  return <div className={classNames}>{children}</div>;
};

export default Card;
