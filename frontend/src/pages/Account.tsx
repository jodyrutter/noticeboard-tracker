import { useState } from "react";
import { api } from "../api/client";
import { useResource } from "../hooks";
import type { Notice, User } from "../types/models";
import { Badge, date, ErrorBox, Icon, State } from "../components/UI";

export function Notifications({ user }: { user: User }) {
  const resource = useResource<Notice[]>(`/notifications/${user.user_id}`);
  const [filter, setFilter] = useState("all"),
    [busy, setBusy] = useState<number | null>(null),
    [error, setError] = useState("");
  const notices =
    resource.data?.filter((n) => filter === "all" || !n.is_read) ?? [];
  async function read(id: number) {
    setBusy(id);
    setError("");
    try {
      await api.put(`/notifications/${id}/read`, {});
      resource.refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">STAY IN THE LOOP</span>
          <h1>Notifications</h1>
          <p>Your updates, without the noise.</p>
        </div>
        <button className="button" onClick={resource.refresh}>
          ↻ Refresh
        </button>
      </div>
      <div className="toolbar">
        <div className="segmented">
          <button
            className={filter === "all" ? "active" : ""}
            onClick={() => setFilter("all")}
          >
            All updates
          </button>
          <button
            className={filter === "unread" ? "active" : ""}
            onClick={() => setFilter("unread")}
          >
            Unread
          </button>
        </div>
        <span className="muted">
          {resource.data?.filter((n) => !n.is_read).length ?? 0} unread
        </span>
      </div>
      {error && <ErrorBox error={error} />}
      <State {...resource} retry={resource.refresh} empty={!notices.length}>
        <div className="notice-list">
          {notices.map((n) => (
            <article
              key={n.id}
              className={n.is_read ? "notice" : "notice unread"}
            >
              <span className="notice-icon">
                <Icon name="notifications" />
              </span>
              <div>
                <small>
                  {date(n.created_at)}{" "}
                  {!n.is_read && <span className="unread-dot" />}
                </small>
                <p>{n.message}</p>
              </div>
              {!n.is_read && (
                <button
                  className="text-button"
                  disabled={busy === n.id}
                  onClick={() => void read(n.id)}
                >
                  {busy === n.id ? "Saving…" : "Mark read"}
                </button>
              )}
            </article>
          ))}
        </div>
      </State>
    </>
  );
}
export function Account({ user }: { user: User }) {
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">A SPACE THAT’S YOURS</span>
          <h1>My account</h1>
          <p>Your identity in the Noticeboard workspace.</p>
        </div>
      </div>
      <section className="profile-card">
        <div className="profile-cover" />
        <div className="profile-body">
          <span className="avatar large">{user.name.slice(0, 1)}</span>
          <h2>{user.name}</h2>
          <Badge value={user.role} />
          <dl>
            <div>
              <dt>Email address</dt>
              <dd>{user.email}</dd>
            </div>
            <div>
              <dt>User account ID</dt>
              <dd>#{user.user_id}</dd>
            </div>
            <div>
              <dt>Workspace role</dt>
              <dd>
                {user.role === "HR"
                  ? "Human resources"
                  : user.role === "MANAGER"
                    ? "Training manager"
                    : "Trainee"}
              </dd>
            </div>
          </dl>
          <p className="panel-note">
            HR can find your account by email for onboarding. Contact your team
            administrator to update your account details.
          </p>
        </div>
      </section>
    </>
  );
}
