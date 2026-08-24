import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import {
  rolePermissions,
  type RolePermissions,
  type UserRole,
} from "../lib/roleAccess";

export type { RolePermissions, UserRole } from "../lib/roleAccess";

export interface RoleContextValue {
  role: UserRole | null;
  permissions: RolePermissions;
  login: (role: UserRole) => void;
  logout: () => void;
}

interface RoleProviderProps {
  children: ReactNode;
  initialRole?: UserRole | null;
}

const emptyPermissions = rolePermissions("client");
const RoleContext = createContext<RoleContextValue | undefined>(undefined);

export function RoleProvider({ children, initialRole = null }: RoleProviderProps) {
  const [role, setRole] = useState<UserRole | null>(initialRole);
  const value = useMemo<RoleContextValue>(
    () => ({
      role,
      permissions: role ? rolePermissions(role) : emptyPermissions,
      login: setRole,
      logout: () => setRole(null),
    }),
    [role],
  );

  return <RoleContext.Provider value={value}>{children}</RoleContext.Provider>;
}

export function useRole(): RoleContextValue {
  const context = useContext(RoleContext);
  if (!context) {
    throw new Error("useRole must be used within a RoleProvider");
  }
  return context;
}
