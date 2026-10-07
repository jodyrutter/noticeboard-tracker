import { authStore } from "../auth/authStore";

const BASE_URL = import.meta.env.PROD
  ? "/backend"
  : (import.meta.env.VITE_API_URL ?? "/backend");

export class ApiError extends Error {
  status: number;
  detail?: string;
  constructor(status: number, message: string, detail?: string) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

function getErrorDetail(body: unknown, fallback: string): string {
  if (typeof body !== "object" || body === null) {
    return fallback;
  }

  const detail = (body as { detail?: unknown }).detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail.flatMap((item: unknown) => {
      if (typeof item !== "object" || item === null) {
        return [];
      }

      const error = item as { loc?: unknown; msg?: unknown };

      if (typeof error.msg !== "string") {
        return [];
      }

      const field = Array.isArray(error.loc)
        ? error.loc
            .filter((part) => part !== "body")
            .map(String)
            .join(".")
        : "";

      return [field ? `${field}: ${error.msg}` : error.msg];
    });

    return messages.length > 0 ? messages.join("; ") : fallback;
  }

  return fallback;
}

const REQUEST_TIMEOUT_MS = 15_000;

async function fetchWithTimeout(
  url: string,
  init: RequestInit,
): Promise<{ response: Response; text: string }> {
  const controller = new AbortController();
  let timedOut = false;

  const timer = window.setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(url, { ...init, signal: controller.signal });

    const text = await response.text();

    return { response, text };
  } catch {
    if (timedOut) {
      const method = (init.method ?? "GET").toUpperCase();
      const isRead = method === "GET" || method === "HEAD";

      throw new ApiError(
        0,
        isRead
          ? "The request took too long. Please try again."
          : "The request timed out. It may have completed. Check the latest information before submitting it again.",
      );
    }

    throw new ApiError(
      0,
      "Couldn't reach the noticeboard service. Check your connection and try again.",
    );
  } finally {
    window.clearTimeout(timer);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const session = authStore.get();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init?.headers as Record<string, string>) ?? {}),
  };
  if (session) headers["Authorization"] = `Bearer ${session.token}`;
  const { response, text } = await fetchWithTimeout(`${BASE_URL}${path}`, {
    ...init,
    headers,
  });

  const isLoginRequest =
    path === "/api/login" ||
    path === "/api/login/customer" ||
    path === "/api/login/admin";

  if (
    response.status === 401 &&
    session &&
    !isLoginRequest &&
    authStore.get()?.token === session.token
  ) {
    sessionStorage.setItem(
      "auth-notice",
      "Your session expired or is no longer valid. Please sign in again.",
    );
    authStore.clear();
  }

  if (response.status === 204) return undefined as T;

  let body: unknown = null;

  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    if (response.ok) {
      throw new ApiError(
        response.status,
        "The noticeboard service returned an unexpected response.",
      );
    }
  }

  if (!response.ok) {
    let detail: string;

    if (response.status === 429) {
      detail = "Too many attempts. Please wait a minute and try again.";
    } else if (response.status >= 500) {
      detail =
        "The noticeboard service encountered a problem. Please try again later.";
    } else {
      const fallback =
        response.status === 403
          ? "You don't have permission to perform this action."
          : response.status === 409
            ? "This request conflicts with an existing record."
            : response.status === 422
              ? "Please check the information you entered."
              : "The request could not be completed.";

      detail = getErrorDetail(body, fallback);
    }

    throw new ApiError(response.status, detail, detail);
  }

  return body as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  del: (path: string) => request<void>(path, { method: "DELETE" }),
};
