import { type ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useRole } from "./RoleContext";

interface RequirePmRoleProps {
  children: ReactNode;
}

export default function RequirePmRole({ children }: RequirePmRoleProps) {
  const { role } = useRole();

  return role === "pm" ? children : <Navigate to="/projects" replace />;
}
