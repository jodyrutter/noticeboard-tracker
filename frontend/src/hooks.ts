import { useCallback, useEffect, useState } from "react";
import { api } from "./api/client";
import { authStore } from "./auth/authStore";
import type { AuthSession } from "./types/auth";

export function useResource<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [version, setVersion] = useState(0);
  const refresh = useCallback(() => setVersion((v) => v + 1), []);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    setData(null);
    api
      .get<T>(path)
      .then((value) => {
        if (active) setData(value);
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [path, version]);
  return { data, error, loading, refresh };
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
