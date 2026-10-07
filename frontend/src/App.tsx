import { useEffect, useState } from "react";
import { api } from "./api/client";
import { useAuth } from "./auth/useAuth";
import { usePathname } from "./auth/usePathname";
import { useResource, useSessionExpiration } from "./hooks";
import { AuthScreen } from "./components/AuthScreen";
import { ErrorBox, Icon, Logo, State } from "./components/UI";
import { Overview } from "./pages/Overview";
import { Plans } from "./pages/Plans";
import { Trainees, Cohorts } from "./pages/People";
import { Account, Notifications } from "./pages/Account";
import type { User } from "./types/models";

export default function App() {
  const { session, logout } = useAuth();
  const routing = usePathname();
  useSessionExpiration(session);
  if (!session)
    return (
      <AuthScreen
        key={routing.path}
        signup={routing.path === "/app/signup"}
        navigate={routing.navigate}
      />
    );
  return <Workspace key={session.token} logout={logout} {...routing} />;
}

function Workspace({
  logout,
  path,
  navigate,
  replace,
}: {
  logout: () => void;
  path: string;
  navigate: (p: string) => void;
  replace: (p: string) => void;
}) {
  const profile = useResource<User>("/api/me");
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [menu, setMenu] = useState(false);
  const user = profile.data;
  const items = user
    ? [
        ...(user.role === "MANAGER"
          ? [{ id: "overview", label: "Overview" }]
          : []),
        ...(user.role !== "HR"
          ? [
              {
                id: "plans",
                label:
                  user.role === "TRAINEE"
                    ? "My learning plans"
                    : "Training plans",
              },
            ]
          : []),
        ...(user.role !== "TRAINEE"
          ? [
              { id: "trainees", label: "Trainees" },
              { id: "cohorts", label: "Cohorts" },
            ]
          : []),
        ...(user.role === "HR"
          ? [{ id: "plans", label: "My learning plans" }]
          : []),
        { id: "notifications", label: "Notifications" },
        { id: "profile", label: "My account" },
      ]
    : [];
  const page = path.split("/")[2] || "";
  useEffect(() => {
    if (user && !items.some((i) => i.id === page))
      replace(`/app/${items[0].id}`);
  }, [user, page, replace]);
  useEffect(() => {
    const refresh = () => profile.refresh();
    window.addEventListener("focus", refresh);
    return () => window.removeEventListener("focus", refresh);
  }, [profile.refresh]);
  function go(id: string) {
    navigate(`/app/${id}`);
    setMenu(false);
  }
  async function signout() {
    setBusy(true);
    setError("");
    try {
      await api.post("/api/logout", {});
      sessionStorage.setItem("auth-notice", "You’ve been signed out.");
      logout();
      navigate("/app/signin");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (!user)
    return (
      <div className="startup">
        <Logo />
        <State {...profile} retry={profile.refresh}>
          <span />
        </State>
        {profile.error && (
          <button className="button" onClick={() => void signout()}>
            Sign out
          </button>
        )}
        {error && <ErrorBox error={error} />}
      </div>
    );
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside className={`sidebar ${menu ? "open" : ""}`}>
        <div className="sidebar-brand">
          <Logo />
          <span>THE TRAINING WORKSPACE</span>
        </div>
        <div className="workspace-label">
          <span className="workspace-icon">N</span>
          <div>
            <strong>Your workspace</strong>
            <small>
              {user.role === "HR"
                ? "People & onboarding"
                : user.role === "MANAGER"
                  ? "Learning & development"
                  : "Your learning journey"}
            </small>
          </div>
        </div>
        <span className="nav-caption">WORKSPACE</span>
        <nav aria-label="Main navigation">
          {items.map((i) => (
            <a
              href={`/app/${i.id}`}
              key={i.id}
              aria-current={page === i.id ? "page" : undefined}
              onClick={(e) => {
                if (!e.ctrlKey && !e.metaKey) {
                  e.preventDefault();
                  go(i.id);
                }
              }}
            >
              <Icon name={i.id} />
              {i.label}
              {page === i.id && <span className="nav-indicator" />}
            </a>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-note">
            <span>↗</span>
            <p>
              A little progress,
              <br />
              every day.
            </p>
          </div>
          <button className="sidebar-user" onClick={() => go("profile")}>
            <span className="avatar">{user.name.slice(0, 1)}</span>
            <span>
              <strong>{user.name}</strong>
              <small>{user.role.toLowerCase()}</small>
            </span>
            <Icon name="arrow" />
          </button>
        </div>
      </aside>
      {menu && (
        <button
          className="sidebar-scrim"
          aria-label="Close navigation"
          onClick={() => setMenu(false)}
        />
      )}
      <div className="workspace">
        <header className="topbar">
          <div>
            <button
              className="icon-button mobile-menu"
              aria-label="Toggle navigation"
              aria-expanded={menu}
              onClick={() => setMenu(!menu)}
            >
              ☰
            </button>
            <span className="breadcrumb">
              Workspace <span>/</span>{" "}
              <strong>
                {items.find((i) => i.id === page)?.label ?? "Overview"}
              </strong>
            </span>
          </div>
          <div className="top-actions">
            <span className="today">
              {new Date().toLocaleDateString("en-US", {
                weekday: "short",
                month: "short",
                day: "numeric",
              })}
            </span>
            <button
              className="icon-button"
              aria-label="Open notifications"
              onClick={() => go("notifications")}
            >
              <Icon name="notifications" />
            </button>
            <button
              className="text-button"
              disabled={busy}
              onClick={() => void signout()}
            >
              {busy ? "Signing out…" : "Sign out"}
            </button>
          </div>
        </header>
        <main id="main" key={`${page}-${user.role}`}>
          {error && <ErrorBox error={error} />}
          {page === "overview" && user.role === "MANAGER" && (
            <Overview user={user} navigate={go} />
          )}
          {page === "plans" && <Plans user={user} />}
          {page === "trainees" && user.role !== "TRAINEE" && (
            <Trainees user={user} />
          )}
          {page === "cohorts" && user.role !== "TRAINEE" && (
            <Cohorts user={user} />
          )}
          {page === "notifications" && <Notifications user={user} />}
          {page === "profile" && <Account user={user} />}
        </main>
        <footer className="workspace-footer">
          <span>Noticeboard</span>
          <span>Make progress visible.</span>
        </footer>
      </div>
    </div>
  );
}
