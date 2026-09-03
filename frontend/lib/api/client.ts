import { clearSession, getAccessToken } from "@/lib/auth/session";
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

function handleUnauthorized(status: number): void {
  if (status !== 401) return;
  clearSession();
  if (typeof window !== "undefined") {
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.assign(`/login?next=${next}`);
  }
}

export type RequestOptions = {
  method?: string;
  body?: unknown;
  auth?: boolean;
  headers?: Record<string, string>;
};

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
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
    handleUnauthorized(401);
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
