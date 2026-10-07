import { useResource } from "../hooks";
import type { Summary, User } from "../types/models";
import { Badge, Icon, State } from "../components/UI";

interface OverviewTrainee {
  trainee_id: number;
  name: string;
  email: string;
  cohort: string | null;
  status: string;
}
export function Overview({
  user,
  navigate,
}: {
  user: User;
  navigate: (page: string) => void;
}) {
  const summary = useResource<Summary>("/dashboard"),
    people = useResource<OverviewTrainee[]>("/dashboard/trainees");
  const s = summary.data;
  const reports = s
    ? s.completed_reports + s.in_progress_reports + s.blocked_reports
    : 0;
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">THE BIG PICTURE</span>
          <h1>Your team, moving forward.</h1>
          <p>
            Welcome back, {user.name.split(" ")[0]}. Here’s where things stand.
          </p>
        </div>
        <button
          className="button"
          onClick={() => {
            summary.refresh();
            people.refresh();
          }}
        >
          ↻ Refresh overview
        </button>
      </div>
      <section className="welcome-banner">
        <div>
          <span className="eyebrow">SMALL STEPS. MEANINGFUL PROGRESS.</span>
          <h2>
            Give potential
            <br />a place to grow.
          </h2>
          <p>Bring learning plans, people, and progress together.</p>
          <button className="button light" onClick={() => navigate("plans")}>
            Explore training plans <Icon name="arrow" />
          </button>
        </div>
        <div className="banner-art" aria-hidden="true">
          <div className="art-orbit" />
          <div className="art-note">
            <span>THE NEXT CHAPTER</span>
            <b>
              Onward
              <br />& upward.
            </b>
            <i>↗</i>
          </div>
          <div className="art-tag">✓ Made for progress</div>
        </div>
      </section>
      <State {...summary} retry={summary.refresh}>
        <div className="stats">
          {[
            {
              label: "Total trainees",
              value: s?.total_trainees,
              note: `${s?.active_trainees ?? 0} active learners`,
              icon: "trainees",
            },
            {
              label: "Training cohorts",
              value: s?.total_cohorts,
              note: "Learning together",
              icon: "cohorts",
            },
            {
              label: "Completed reports",
              value: s?.completed_reports,
              note: "Milestones worth celebrating",
              icon: "plans",
            },
            {
              label: "Awaiting an update",
              value: s?.missing_reports,
              note: "Assignments without a report",
              icon: "notifications",
            },
          ].map((item, i) => (
            <article className="stat" key={item.label}>
              <div>
                <span>{item.label}</span>
                <span className={`stat-icon tone-${i % 3}`}>
                  <Icon name={item.icon} />
                </span>
              </div>
              <strong>{item.value ?? "—"}</strong>
              <small>{item.note}</small>
            </article>
          ))}
        </div>
      </State>
      <div className="overview-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">PEOPLE & POSSIBILITIES</span>
              <h2>Your trainees</h2>
            </div>
            <button
              className="text-button"
              onClick={() => navigate("trainees")}
            >
              View all <Icon name="arrow" />
            </button>
          </div>
          <State
            {...people}
            retry={people.refresh}
            empty={!people.data?.length}
          >
            <div className="people-list">
              {people.data?.slice(0, 5).map((p) => (
                <div className="people-row" key={p.trainee_id}>
                  <span className="avatar">{p.name.slice(0, 1)}</span>
                  <div>
                    <strong>{p.name}</strong>
                    <small>{p.cohort || "No cohort assigned"}</small>
                  </div>
                  <Badge value={p.status} />
                </div>
              ))}
            </div>
          </State>
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">LEARNING PULSE</span>
              <h2>Report activity</h2>
            </div>
            <Icon name="plans" />
          </div>
          <State {...summary} retry={summary.refresh}>
            <div className="report-total">
              <strong>{reports}</strong>
              <span>progress reports submitted</span>
            </div>
            <div className="stacked-bar" aria-label="Report status breakdown">
              {s &&
                [
                  { n: s.completed_reports, c: "complete" },
                  { n: s.in_progress_reports, c: "inprogress" },
                  { n: s.blocked_reports, c: "blocked" },
                ].map((x) => (
                  <span
                    key={x.c}
                    className={x.c}
                    style={{ width: `${reports ? (x.n / reports) * 100 : 0}%` }}
                  />
                ))}
            </div>
            <div className="legend">
              {s &&
                [
                  ["Completed", s.completed_reports, "complete"],
                  ["In progress", s.in_progress_reports, "inprogress"],
                  ["Blocked", s.blocked_reports, "blocked"],
                ].map(([label, value, c]) => (
                  <div key={label}>
                    <span className={`dot ${c}`} />
                    <span>{label}</span>
                    <strong>{value}</strong>
                  </div>
                ))}
            </div>
            <p className="panel-note">
              Counts reflect submitted reports, not unique plans or learners.
            </p>
          </State>
        </section>
      </div>
    </>
  );
}
