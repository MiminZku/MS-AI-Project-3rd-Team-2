export type UserRole = "pm" | "client";

export interface RolePermissions {
  viewFullTranscript: boolean;
  viewOperationalSessions: boolean;
  viewPowerBiDataset: boolean;
  viewRecording: boolean;
  viewObserverControls: boolean;
}

export const rolePermissions = (role: UserRole): RolePermissions =>
  role === "pm"
    ? {
        viewFullTranscript: true,
        viewOperationalSessions: true,
        viewPowerBiDataset: true,
        viewRecording: true,
        viewObserverControls: true,
      }
    : {
        viewFullTranscript: false,
        viewOperationalSessions: false,
        viewPowerBiDataset: false,
        viewRecording: false,
        viewObserverControls: false,
      };
