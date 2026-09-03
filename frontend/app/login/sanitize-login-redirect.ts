export const DEFAULT_LOGIN_REDIRECT = "/wardrobe";

/**
 * Resolve a post-login redirect target from the `next` query param.
 * Accepts same-origin relative paths only; rejects external/protocol-relative URLs.
 */
export function sanitizeLoginRedirect(
  next: string | null | undefined,
  defaultPath: string = DEFAULT_LOGIN_REDIRECT,
): string {
  if (next == null) return defaultPath;

  const trimmed = next.trim();
  if (!trimmed) return defaultPath;

  if (trimmed.includes("\\")) return defaultPath;
  if (!trimmed.startsWith("/") || trimmed.startsWith("//")) return defaultPath;
  if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(trimmed)) return defaultPath;
  if (trimmed.includes("://")) return defaultPath;

  return trimmed;
}
