import { useCallback, useEffect, useState } from "react";

export function usePathname() {
  const [path, setPath] = useState(window.location.pathname);

  useEffect(() => {
    const onPop = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const navigate = useCallback((to: string) => {
    if (window.location.pathname === to) return;
    window.history.pushState({}, "", to);
    setPath(to);
  }, []);

  const replace = useCallback((to: string) => {
    window.history.replaceState({}, "", to);
    setPath(to);
  }, []);

  return { path, navigate, replace };
}
