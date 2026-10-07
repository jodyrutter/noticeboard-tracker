import type { AuthSession } from "../types/auth";

const STORAGE_KEY = "noticeboard_auth";
const CHANGE_EVENT = "noticeboard:auth-changed";

function read(): AuthSession | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as AuthSession;
  } catch {
    return null;
  }
}

function write(session: AuthSession | null) {
  if (session) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  } else {
    localStorage.removeItem(STORAGE_KEY);
  }
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

export const authStore = {
  get(): AuthSession | null {
    return read();
  },
  set(session: AuthSession) {
    write(session);
  },
  clear() {
    write(null);
  },
  subscribe(listener: () => void): () => void {
    const handler = () => listener();
    window.addEventListener(CHANGE_EVENT, handler);
    window.addEventListener("storage", handler);
    return () => {
      window.removeEventListener(CHANGE_EVENT, handler);
      window.removeEventListener("storage", handler);
    };
  },
};
