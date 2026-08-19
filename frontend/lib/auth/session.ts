const TOKEN_KEY = "sveyra_access_token";
const USER_ID_KEY = "sveyra_user_id";

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof sessionStorage !== "undefined";
}

export function getAccessToken(): string | null {
  if (!canUseStorage()) return null;
  return sessionStorage.getItem(TOKEN_KEY);
}

export function getUserId(): string | null {
  if (!canUseStorage()) return null;
  return sessionStorage.getItem(USER_ID_KEY);
}

export function setSession(accessToken: string, userId: string): void {
  if (!canUseStorage()) return;
  sessionStorage.setItem(TOKEN_KEY, accessToken);
  sessionStorage.setItem(USER_ID_KEY, userId);
}

export function clearSession(): void {
  if (!canUseStorage()) return;
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_ID_KEY);
}

/** Decode JWT payload without verification (client UX only; server still validates). */
export function userIdFromAccessToken(token: string): string | null {
  try {
    const parts = token.split(".");
    if (parts.length < 2 || !parts[1]) return null;
    const normalized = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), "=");
    const payload = JSON.parse(atob(padded)) as { sub?: unknown };
    return typeof payload.sub === "string" ? payload.sub : null;
  } catch {
    return null;
  }
}

const MEDIA_MAP_KEY = "sveyra_item_media";

export function rememberMediaAsset(itemId: string, assetId: string): void {
  if (!canUseStorage()) return;
  const raw = sessionStorage.getItem(MEDIA_MAP_KEY);
  const map = raw ? (JSON.parse(raw) as Record<string, string>) : {};
  map[itemId] = assetId;
  sessionStorage.setItem(MEDIA_MAP_KEY, JSON.stringify(map));
}

export function getRememberedMediaAsset(itemId: string): string | null {
  if (!canUseStorage()) return null;
  const raw = sessionStorage.getItem(MEDIA_MAP_KEY);
  if (!raw) return null;
  try {
    const map = JSON.parse(raw) as Record<string, string>;
    return map[itemId] ?? null;
  } catch {
    return null;
  }
}

export function forgetMediaAsset(itemId: string): void {
  if (!canUseStorage()) return;
  const raw = sessionStorage.getItem(MEDIA_MAP_KEY);
  if (!raw) return;
  try {
    const map = JSON.parse(raw) as Record<string, string>;
    delete map[itemId];
    sessionStorage.setItem(MEDIA_MAP_KEY, JSON.stringify(map));
  } catch {
    /* ignore */
  }
}
