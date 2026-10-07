import { useState } from "react";
import { useResource } from "../hooks";
import { Badge, date, Search, State } from "../components/UI";

type Assignment = {
  trainee_id: number;
  name: string;
  email: string;
  cohort: string | null;
  plan_id: number;
  title: string;
  due_date: string | null;
  status: string;
  last_report_at: string | null;
  missing_report: boolean;
  overdue: boolean;
};
type TrackingData = {
  summary: Record<string, number>;
  assignments: Assignment[];
  unassigned_trainees: {
    trainee_id: number;
    name: string;
    email: string;
    cohort: string | null;
  }[];
};
export function Tracking() {
  const resource = useResource<TrackingData>("/dashboard/tracking");
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const rows =
    resource.data?.assignments.filter(
      (r) =>
        `${r.name} ${r.email} ${r.title} ${r.cohort ?? ""}`
          .toLowerCase()
          .includes(query.toLowerCase()) &&
        (filter === "all" ||
          (filter === "overdue"
            ? r.overdue
            : filter === "missing"
              ? r.missing_report
              : r.status === filter)),
    ) ?? [];
  return (
    <section className="promotion-section tracking-section">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">CURRENT ASSIGNMENTS</span>
          <h2>Who needs attention?</h2>
        </div>
        <button className="button" onClick={resource.refresh}>
          Refresh tracking
        </button>
      </div>
      <State {...resource} retry={resource.refresh}>
        <div className="stats">
          {[
            ["Assignments", "total_assignments"],
            ["Completed", "COMPLETED"],
            ["Blocked", "BLOCKED"],
            ["Overdue", "overdue"],
            ["Missing reports", "missing_reports"],
            ["Active trainees without plans", "unassigned_trainees"],
          ].map(([label, key]) => (
            <article className="stat" key={key}>
              <span>{label}</span>
              <strong>{resource.data?.summary[key] ?? 0}</strong>
            </article>
          ))}
        </div>
        <div className="toolbar">
          <Search
            value={query}
            onChange={setQuery}
            placeholder="Search tracking by trainee, plan or cohort…"
          />
          <label className="field">
            Tracking filter
            <select value={filter} onChange={(e) => setFilter(e.target.value)}>
              <option value="all">All assignments</option>
              <option value="overdue">Overdue</option>
              <option value="missing">No report yet</option>
              {["NOT_STARTED", "IN_PROGRESS", "COMPLETED", "BLOCKED"].map(
                (s) => (
                  <option key={s} value={s}>
                    {s.replaceAll("_", " ")}
                  </option>
                ),
              )}
            </select>
          </label>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Trainee</th>
                <th>Cohort</th>
                <th>Plan</th>
                <th>Latest status</th>
                <th>Last update</th>
                <th>Due</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={`${r.trainee_id}-${r.plan_id}`}>
                  <td>
                    {r.name}
                    <small className="muted"> {r.email}</small>
                  </td>
                  <td>{r.cohort || "Solo track"}</td>
                  <td>{r.title}</td>
                  <td>
                    <Badge value={r.status} />
                    {r.overdue && (
                      <span className="badge blocked">Overdue</span>
                    )}
                  </td>
                  <td>
                    {r.missing_report
                      ? "No report yet"
                      : date(r.last_report_at)}
                  </td>
                  <td>{date(r.due_date)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!rows.length && (
            <p className="panel-note">No matching assignments.</p>
          )}
        </div>
        <h3>Active trainees without a plan</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Cohort</th>
              </tr>
            </thead>
            <tbody>
              {resource.data?.unassigned_trainees.map((t) => (
                <tr key={t.trainee_id}>
                  <td>{t.name}</td>
                  <td>{t.email}</td>
                  <td>{t.cohort || "Solo track"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!resource.data?.unassigned_trainees.length && (
            <p className="panel-note">Every active trainee has a plan.</p>
          )}
        </div>
        <p className="panel-note">
          One latest report per trainee and plan. Overdue means the due date has
          passed and the latest status is not completed. Historical report
          counts above remain a separate activity measure.
        </p>
      </State>
    </section>
  );
}
