import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import { authStore } from "../auth/authStore";
import type { LoginResponse } from "../types/auth";
import { ErrorBox, Icon, Logo } from "./UI";

export function AuthScreen({
  signup,
  navigate,
}: {
  signup: boolean;
  navigate: (path: string) => void;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [notice, setNotice] = useState(() => {
    const value = sessionStorage.getItem("auth-notice") ?? "";
    return value;
  });
  useEffect(() => {
    sessionStorage.removeItem("auth-notice");
  }, []);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const values = Object.fromEntries(new FormData(e.currentTarget)) as Record<
      string,
      string
    >;
    if (
      signup &&
      (values.password.length < 8 || !/[^a-zA-Z0-9]/.test(values.password))
    ) {
      setError("Use at least 8 characters and one special character.");
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      if (signup) {
        await api.post("/api/signup", values);
        sessionStorage.setItem(
          "auth-notice",
          "Your account is ready. Sign in to get started.",
        );
        navigate("/app/signin");
      } else {
        const result = await api.post<LoginResponse>("/api/login", values);
        authStore.set({ token: result.access_token, email: values.email });
        navigate("/app");
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="auth-page">
      <section className="auth-story">
        <Logo />
        <div className="story-copy">
          <span className="eyebrow">
            A LITTLE STRUCTURE. A LOT OF POSSIBILITY.
          </span>
          <h1>
            Great progress
            <br />
            starts with
            <br />
            <em>a clear plan.</em>
          </h1>
          <p>
            A shared space for your people, training plans, and the next step
            forward.
          </p>
          <div className="paper-stack" aria-hidden="true">
            <div className="paper back" />
            <div className="paper front">
              <span className="pin" />
              <small>THE NOTICEBOARD WAY</small>
              <h3>
                Learn. Practice.
                <br />
                Move forward.
              </h3>
              <div className="paper-line" />
              <div className="paper-line short" />
              <span className="paper-check">✓ One step at a time</span>
            </div>
          </div>
        </div>
        <footer>
          YOUR GROWTH, IN GOOD COMPANY. <span>↗</span>
        </footer>
      </section>
      <section className="auth-form">
        <div className="auth-mobile-logo">
          <Logo />
        </div>
        <div className="auth-form-inner">
          <span className="eyebrow">YOUR TRAINING WORKSPACE</span>
          <h2>{signup ? "Start your next chapter." : "Welcome back."}</h2>
          <p className="muted">
            {signup
              ? "Create your trainee account. Your team will take it from here."
              : "Sign in to pick up where you left off."}
          </p>
          {notice && (
            <div role="status" className="success-box">
              {notice}
            </div>
          )}
          <form onSubmit={submit}>
            {signup && (
              <label className="field">
                Full name
                <input
                  name="name"
                  autoComplete="name"
                  required
                  maxLength={100}
                  placeholder="Alex Morgan"
                />
              </label>
            )}
            <label className="field">
              Email address
              <input
                name="email"
                type="email"
                autoComplete="email"
                required
                maxLength={150}
                placeholder="you@example.com"
              />
            </label>
            <label className="field">
              <span id="password-label">Password</span>
              <input
                aria-labelledby="password-label"
                aria-describedby={signup ? "password-hint" : undefined}
                name="password"
                type="password"
                autoComplete={signup ? "new-password" : "current-password"}
                minLength={signup ? 8 : 1}
                maxLength={1024}
                required
                placeholder={
                  signup ? "Create a strong password" : "Enter your password"
                }
              />
              {signup && (
                <small id="password-hint">
                  At least 8 characters, including a special character.
                </small>
              )}
            </label>
            {error && <ErrorBox error={error} />}
            <button className="button primary full" disabled={busy}>
              {busy ? "Please wait…" : signup ? "Create account" : "Sign in"}
              <Icon name="arrow" />
            </button>
          </form>
          <p className="auth-switch">
            {signup ? "Already part of the team?" : "New to Noticeboard?"}{" "}
            <button
              className="text-button"
              onClick={() => navigate(signup ? "/app/signin" : "/app/signup")}
            >
              {signup ? "Sign in" : "Create an account"}
            </button>
          </p>
          <div className="auth-note">
            <span>◎</span> One workspace. The right tools for your role.
          </div>
        </div>
        <footer>Noticeboard · A clearer path to progress</footer>
      </section>
    </div>
  );
}
