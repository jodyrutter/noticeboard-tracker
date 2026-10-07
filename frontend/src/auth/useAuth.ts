import { useEffect, useState, useCallback } from "react";
import { authStore } from "./authStore";
import type { AuthSession } from "../types/auth";

export function useAuth() {
  const [session, setSession] = useState<AuthSession | null>(() =>
    authStore.get(),
  );

  useEffect(() => {
    return authStore.subscribe(() => setSession(authStore.get()));
  }, []);

  const login = useCallback((s: AuthSession) => authStore.set(s), []);
  const logout = useCallback(() => authStore.clear(), []);

  return { session, login, logout };
}
