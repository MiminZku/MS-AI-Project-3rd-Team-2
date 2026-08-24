const STORAGE_KEY = "gromit.client-project-grant";

export interface ClientProjectGrant {
  projectId: string;
  accessToken: string;
}

export function saveClientProjectGrant(grant: ClientProjectGrant): void {
  window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(grant));
}

export function loadClientProjectGrant(): ClientProjectGrant | null {
  try {
    const rawGrant = window.sessionStorage.getItem(STORAGE_KEY);
    if (!rawGrant) return null;
    const grant = JSON.parse(rawGrant) as Partial<ClientProjectGrant>;
    if (typeof grant.projectId !== "string" || typeof grant.accessToken !== "string") {
      return null;
    }
    return { projectId: grant.projectId, accessToken: grant.accessToken };
  } catch {
    return null;
  }
}

export function clearClientProjectGrant(): void {
  window.sessionStorage.removeItem(STORAGE_KEY);
}
