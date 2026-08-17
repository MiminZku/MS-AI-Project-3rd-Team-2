import React from "react";
import { Link } from "react-router-dom";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md" | "lg";
  to?: string;
  href?: string;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = "primary",
  size = "md",
  to,
  href,
  className = "",
  ...props
}) => {
  const classNames = `btn btn-${variant} btn-${size} ${className}`;

  if (to) {
    return (
      <Link to={to} className={classNames} {...(props as any)}>
        {children}
      </Link>
    );
  }

  if (href) {
    return (
      <a href={href} className={classNames} target="_blank" rel="noopener noreferrer" {...(props as any)}>
        {children}
      </a>
    );
  }

  return (
    <button className={classNames} {...props}>
      {children}
    </button>
  );
};

export default Button;
