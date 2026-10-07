import { useCallback, useEffect, useState } from "react";
import { api } from "./api/client";
import { authStore } from "./auth/authStore";
import type { AuthSession } from "./types/auth";

const pendingReads = new Map<string, Promise<unknown>>();

function readResource<T>(path: string): Promise<T> {
  const key = `${authStore.get()?.token ?? "anonymous"}:${path}`;
  let request = pendingReads.get(key);
  if (!request) {
    request = api.get<T>(path).finally(() => pendingReads.delete(key));
    pendingReads.set(key, request);
  }
  return request as Promise<T>;
}

export function useResource<T>(path: string) {
  const [result, setResult] = useState<{ path: string; data: T } | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(true);
  const [version, setVersion] = useState(0);
  const refresh = useCallback(() => setVersion((v) => v + 1), []);
  const data = result?.path === path ? result.data : null;
  useEffect(() => {
    let active = true;
    setPending(true);
    setError("");
    readResource<T>(path)
      .then((value) => {
        if (active) setResult({ path, data: value });
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setPending(false);
      });
    return () => {
      active = false;
    };
  }, [path, version]);
  return {
    data,
    error,
    loading: pending && data === null,
    refreshing: pending && data !== null,
    hasData: data !== null,
    refresh,
  };
}

export function useSessionExpiration(session: AuthSession | null) {
  useEffect(() => {
    if (!session) return;
    const check = () => {
      try {
        const encoded = session.token
          .split(".")[1]
          .replace(/-/g, "+")
          .replace(/_/g, "/");
        const payload = JSON.parse(
          atob(encoded.padEnd(Math.ceil(encoded.length / 4) * 4, "=")),
        );
        if (
          typeof payload.exp !== "number" ||
          payload.exp * 1000 <= Date.now()
        ) {
          sessionStorage.setItem(
            "auth-notice",
            "Your session expired. Please sign in again.",
          );
          authStore.clear();
        }
      } catch {
        authStore.clear();
      }
    };
    check();
    const timer = window.setInterval(check, 15000);
    window.addEventListener("focus", check);
    return () => {
      clearInterval(timer);
      window.removeEventListener("focus", check);
    };
  }, [session?.token]);
}
