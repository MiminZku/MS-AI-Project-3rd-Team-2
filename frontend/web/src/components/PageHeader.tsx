import React from "react";

interface PageHeaderProps {
  title: string;
  description?: string;
  className?: string;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  description,
  className = "",
}) => {
  return (
    <header className={`page-header ${className}`}>
      <div className="container">
        <h1 className="page-header-title">{title}</h1>
        {description && <p className="page-header-description">{description}</p>}
      </div>
    </header>
  );
};

export default PageHeader;
