import { type ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useRole } from "./RoleContext";

interface RequireRoleProps {
  children: ReactNode;
}

export default function RequireRole({ children }: RequireRoleProps) {
  const { role } = useRole();

  return role === null ? <Navigate to="/login" replace /> : children;
}
