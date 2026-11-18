/** Read the JWT exp claim for display. Does not verify the signature. */
export function tokenExpiryLabel(token: string | null): string | null {
  if (!token) return null;
  const parts = token.split('.');
  if (parts.length < 2) return null;
  try {
    const normalized = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = normalized + '='.repeat((4 - (normalized.length % 4)) % 4);
    const payload = JSON.parse(atob(padded)) as { exp?: number };
    if (!payload.exp) return null;
    return new Date(payload.exp * 1000).toLocaleString();
  } catch {
    return null;
  }
}

export function workspaceLabel(roleName: string | undefined): string {
  if (roleName === 'Infrastructure Inspector') return 'Inspector workspace';
  if (roleName === 'Infrastructure Manager') return 'Manager workspace';
  if (roleName === 'Administrator') return 'Administrator workspace';
  if (roleName === 'Civil Engineer') return 'Civil engineer workspace';
  if (roleName === 'Maintenance Engineer') return 'Maintenance workspace';
  return 'Signed-in workspace';
}
