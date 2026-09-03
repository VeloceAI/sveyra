import { clearSession, getAccessToken, getRefreshToken, setSession, userIdFromAccessToken } from "@/lib/auth/session";
import { ApiError, type ApiErrorBody } from "@/lib/api/types";

function apiBase(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (configured) return configured.replace(/\/$/, "");
  return "";
}

function buildUrl(path: string): string {
  const base = apiBase();
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return `${base}${path.startsWith("/") ? path : `/${path}`}`;
}

async function parseError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as ApiErrorBody;
    if (body?.error?.code && body?.error?.message) {
      return new ApiError(response.status, body.error.code, body.error.message);
    }
  } catch {
    /* fall through */
  }
  return new ApiError(response.status, "http_error", response.statusText || "Request failed");
}

function redirectToLogin(): void {
  clearSession();
  if (typeof window !== "undefined") {
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.assign(`/login?next=${next}`);
  }
}

// Concurrent 401s share one refresh so a page with several in-flight requests
// does not spend its single-use refresh token more than once.
let inFlightRefresh: Promise<boolean> | null = null;

async function refreshSession(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  const response = await fetch(buildUrl("/v1/auth/refresh"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) return false;

  const tokens = (await response.json()) as { access_token: string; refresh_token: string };
  const userId = userIdFromAccessToken(tokens.access_token);
  if (!userId) return false;

  setSession(tokens.access_token, userId, tokens.refresh_token);
  return true;
}

function refreshOnce(): Promise<boolean> {
  if (!inFlightRefresh) {
    inFlightRefresh = refreshSession()
      .catch(() => false)
      .finally(() => {
        inFlightRefresh = null;
      });
  }
  return inFlightRefresh;
}

export type RequestOptions = {
  method?: string;
  body?: unknown;
  auth?: boolean;
  headers?: Record<string, string>;
};

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
  retryAfterRefresh = true,
): Promise<T> {
  const headers: Record<string, string> = { ...(options.headers ?? {}) };
  const auth = options.auth !== false;
  if (auth) {
    const token = getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  if (options.body !== undefined && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(buildUrl(path), {
    method: options.method ?? (options.body !== undefined ? "POST" : "GET"),
    headers,
    body:
      options.body === undefined
        ? undefined
        : options.body instanceof FormData
          ? options.body
          : JSON.stringify(options.body),
  });

  if (response.status === 401) {
    // An expired access token is the common case, so try to renew it and replay
    // the request before sending anyone back to the login screen.
    if (auth && retryAfterRefresh && (await refreshOnce())) {
      return apiRequest<T>(path, options, false);
    }
    redirectToLogin();
    throw await parseError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  if (!response.ok) {
    throw await parseError(response);
  }

  if (response.status === 204 || response.headers.get("content-length") === "0") {
    return undefined as T;
  }

  const text = await response.text();
  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}

export async function apiUpload<T>(
  path: string,
  formData: FormData,
  options: { auth?: boolean } = {},
): Promise<T> {
  return apiRequest<T>(path, {
    method: "POST",
    body: formData,
    auth: options.auth !== false,
  });
}

export function isBrowserLoadableUrl(url: string): boolean {
  const lowered = url.trim().toLowerCase();
  return lowered.startsWith("https://") || lowered.startsWith("http://");
}

export function formatApiError(error: unknown): string {
  if (error instanceof ApiError) {
    return `${error.code}: ${error.message}`;
  }
  if (error instanceof Error) return error.message;
  return "Unexpected error";
}
