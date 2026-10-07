import { useState } from "react";
import { api } from "../api/client";
import { useResource } from "../hooks";
import type { Cohort, Plan, Progress, Trainee, User } from "../types/models";
import {
  Badge,
  date,
  ErrorBox,
  Icon,
  Modal,
  RecordForm,
  Search,
  State,
  type Field,
} from "../components/UI";

function planFields(plan?: Plan): Field[] {
  return [
    { name: "title", label: "Plan title", required: true, value: plan?.title },
    {
      name: "description",
      label: "What will they learn?",
      type: "textarea",
      value: plan?.description,
    },
    {
      name: "due_date",
      label: "Due date",
      type: "date",
      value: plan?.due_date,
    },
  ];
}
function planBody(v: Record<string, string>) {
  return {
    title: v.title,
    description: v.description || null,
    due_date: v.due_date || null,
  };
}

export function Plans({ user }: { user: User }) {
  const resource = useResource<Plan[]>("/plans");
  const [search, setSearch] = useState(""),
    [create, setCreate] = useState(false),
    [selected, setSelected] = useState<Plan | null>(null);
  const manager = user.role === "MANAGER";
  const plans =
    resource.data?.filter((p) =>
      `${p.title} ${p.description ?? ""}`
        .toLowerCase()
        .includes(search.toLowerCase()),
    ) ?? [];
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">
            {manager ? "LEARNING, WITH DIRECTION" : "YOUR NEXT STEPS"}
          </span>
          <h1>{manager ? "Training plans" : "My learning plans"}</h1>
          <p>
            {manager
              ? "Give every trainee a clear path forward."
              : "Everything you’re working toward, in one place."}
          </p>
        </div>
        {manager && (
          <button className="button primary" onClick={() => setCreate(true)}>
            ＋ Create plan
          </button>
        )}
      </div>
      <div className="toolbar">
        <Search
          value={search}
          onChange={setSearch}
          placeholder="Search plans…"
        />
        <span className="muted">
          {plans.length} {plans.length === 1 ? "plan" : "plans"}
        </span>
      </div>
      <State {...resource} retry={resource.refresh} empty={!plans.length}>
        <div className="plan-grid">
          {plans.map((p, index) => (
            <article className="plan-card" key={p.id}>
              <div className="plan-top">
                <span className={`plan-symbol tone-${index % 3}`}>
                  <Icon name="plans" />
                </span>
                <span className="eyebrow">
                  PLAN {String(p.id).padStart(3, "0")}
                </span>
              </div>
              <h2>{p.title}</h2>
              <p>
                {p.description ||
                  "Open this plan to see the details and next steps."}
              </p>
              <div className="plan-bottom">
                <span>
                  <Icon name="cohorts" />{" "}
                  {p.due_date ? `Due ${date(p.due_date)}` : "No deadline"}
                </span>
                <button
                  className="text-button"
                  aria-label={`Open ${p.title}`}
                  onClick={() => setSelected(p)}
                >
                  View plan <Icon name="arrow" />
                </button>
              </div>
            </article>
          ))}
        </div>
      </State>
      {create && (
        <Modal title="Create a training plan" close={() => setCreate(false)}>
          <RecordForm
            fields={planFields()}
            label="Create plan"
            submit={(v) => api.post("/plans", planBody(v))}
            done={() => {
              setCreate(false);
              resource.refresh();
            }}
          />
        </Modal>
      )}
      {selected && (
        <PlanDetails
          plan={selected}
          user={user}
          close={() => setSelected(null)}
          changed={() => {
            setSelected(null);
            resource.refresh();
          }}
        />
      )}
    </>
  );
}

function PlanDetails({
  plan,
  user,
  close,
  changed,
}: {
  plan: Plan;
  user: User;
  close: () => void;
  changed: () => void;
}) {
  const resource = useResource<Plan>(`/plans/${plan.id}`);
  const [mode, setMode] = useState("details"),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const p = resource.data ?? plan;
  const manager = user.role === "MANAGER";
  async function remove() {
    setBusy(true);
    setError("");
    try {
      await api.del(`/plans/${p.id}`);
      changed();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title={p.title} close={close}>
      <State {...resource} retry={resource.refresh}>
        <div className="tabs">
          <button
            className={mode === "details" ? "active" : ""}
            onClick={() => setMode("details")}
          >
            Details
          </button>
          <button
            className={mode === "progress" ? "active" : ""}
            onClick={() => setMode("progress")}
          >
            {manager ? "Progress reports" : "My progress"}
          </button>
          {manager && (
            <>
              <button
                className={mode === "edit" ? "active" : ""}
                onClick={() => setMode("edit")}
              >
                Edit
              </button>
              <button
                className={mode === "assign" ? "active" : ""}
                onClick={() => setMode("assign")}
              >
                Assign
              </button>
            </>
          )}
        </div>
        {mode === "details" && (
          <div className="detail-content">
            <Badge value={manager ? "TRAINING PLAN" : "ASSIGNED TO YOU"} />
            <p className="description">
              {p.description || "No description added."}
            </p>
            <div className="detail-meta">
              <span>
                Due date<strong>{date(p.due_date)}</strong>
              </span>
              <span>
                Plan reference<strong>#{p.id}</strong>
              </span>
            </div>
            {user.role === "TRAINEE" && (
              <button
                className="button primary"
                onClick={() => setMode("report")}
              >
                Share a progress update <Icon name="arrow" />
              </button>
            )}
            {manager && (
              <button
                className="text-button danger"
                onClick={() => setMode("delete")}
              >
                Delete plan
              </button>
            )}
          </div>
        )}
        {mode === "edit" && (
          <RecordForm
            fields={planFields(p)}
            submit={(v) => api.put(`/plans/${p.id}`, planBody(v))}
            done={changed}
          />
        )}
        {mode === "assign" && (
          <AssignPlan plan={p} done={() => setMode("assigned")} />
        )}
        {mode === "assigned" && (
          <div className="success-box" role="status">
            Assignments saved successfully.
          </div>
        )}
        {mode === "report" && (
          <RecordForm
            label="Submit progress"
            fields={[
              {
                name: "status",
                label: "How is it going?",
                required: true,
                value: "IN_PROGRESS",
                options: [
                  { value: "NOT_STARTED", label: "Not started" },
                  { value: "IN_PROGRESS", label: "In progress" },
                  { value: "COMPLETED", label: "Completed" },
                  { value: "BLOCKED", label: "Blocked — I need help" },
                ],
              },
              {
                name: "comments",
                label: "Your update",
                type: "textarea",
                hint: "Share what you’ve learned or where you need support.",
              },
            ]}
            submit={(v) =>
              api.post("/progress", {
                plan_id: p.id,
                status: v.status,
                comments: v.comments || null,
              })
            }
            done={() => setMode("progress")}
          />
        )}
        {mode === "progress" && (
          <ProgressHistory path={`/progress/plan/${p.id}`} manager={manager} />
        )}
        {mode === "delete" && (
          <div className="detail-content">
            <h3>Delete this training plan?</h3>
            <p>
              This permanently removes “{p.title}”. Plans with assignments or
              reports cannot be deleted.
            </p>
            {error && <ErrorBox error={error} />}
            <div className="actions">
              <button className="button" onClick={() => setMode("details")}>
                Keep plan
              </button>
              <button
                className="button danger-button"
                disabled={busy}
                onClick={() => void remove()}
              >
                {busy ? "Deleting…" : "Delete permanently"}
              </button>
            </div>
          </div>
        )}
      </State>
    </Modal>
  );
}

function AssignPlan({ plan, done }: { plan: Plan; done: () => void }) {
  const trainees = useResource<Trainee[]>("/trainees");
  const cohorts = useResource<Cohort[]>("/cohorts");
  const assignments = useResource<{ trainee_ids: number[] }>(
    `/plans/${plan.id}/assignments`,
  );
  return (
    <State {...assignments} retry={assignments.refresh}>
      <State {...trainees} retry={trainees.refresh}>
        <State {...cohorts} retry={cohorts.refresh}>
          {assignments.data && trainees.data && cohorts.data && (
            <AssignmentEditor
              plan={plan}
              done={done}
              trainees={trainees.data}
              cohorts={cohorts.data}
              initial={assignments.data.trainee_ids}
            />
          )}
        </State>
      </State>
    </State>
  );
}

function AssignmentEditor({
  plan,
  done,
  trainees,
  cohorts,
  initial,
}: {
  plan: Plan;
  done: () => void;
  trainees: Trainee[];
  cohorts: Cohort[];
  initial: number[];
}) {
  const [selected, setSelected] = useState(initial);
  const [target, setTarget] = useState<"trainee" | "cohort">("trainee");
  const [queries, setQueries] = useState({ trainee: "", cohort: "" });
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const add = selected.filter((id) => !initial.includes(id));
  const remove = initial.filter((id) => !selected.includes(id));
  const options =
    target === "trainee"
      ? trainees.map((t) => ({
          id: t.id,
          label: t.name || t.email,
          detail: t.email,
          ids: [t.id],
        }))
      : cohorts.map((c) => ({
          id: c.id,
          label: c.name,
          detail: "Current cohort members",
          ids: trainees.filter((t) => t.cohort_id === c.id).map((t) => t.id),
        }));
  const matches = options.filter((o) =>
    `${o.label} ${o.detail}`
      .toLowerCase()
      .includes(queries[target].toLowerCase()),
  );
  async function save() {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      await api.patch(`/plans/${plan.id}/assignments`, { add, remove });
      done();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="detail-content">
      <p>
        Checked people already have this plan or will receive it when you save.
        Uncheck to remove the assignment. Existing progress reports are kept.
      </p>
      <div className="segmented">
        <button
          disabled={busy}
          className={target === "trainee" ? "active" : ""}
          onClick={() => setTarget("trainee")}
        >
          Trainees
        </button>
        <button
          disabled={busy}
          className={target === "cohort" ? "active" : ""}
          onClick={() => setTarget("cohort")}
        >
          Entire cohort
        </button>
      </div>
      <p>
        {selected.length} trainees selected · {add.length} to add ·{" "}
        {remove.length} to remove
      </p>
      {target === "cohort" && (
        <p>
          A cohort checkbox selects or clears all its current members, including
          individually assigned people. A dash means only some members are
          selected.
        </p>
      )}
      <details className="member-picker" key={target} open>
        <summary>
          Choose {target === "trainee" ? "trainees" : "cohorts"}
        </summary>
        <Search
          value={queries[target]}
          onChange={(query) => setQueries((q) => ({ ...q, [target]: query }))}
          placeholder={`Search ${target === "trainee" ? "trainees" : "cohorts"} to assign…`}
        />
        <div className="member-options">
          {matches.map((o) => {
            const checked =
              o.ids.length > 0 && o.ids.every((id) => selected.includes(id));
            const partial =
              !checked && o.ids.some((id) => selected.includes(id));
            return (
              <label className="member-option" key={o.id}>
                <input
                  type="checkbox"
                  ref={(node) => {
                    if (node) node.indeterminate = partial;
                  }}
                  checked={checked}
                  disabled={busy || !o.ids.length}
                  onChange={(e) => {
                    setError("");
                    setSelected((ids) =>
                      e.target.checked
                        ? [...new Set([...ids, ...o.ids])]
                        : ids.filter((id) => !o.ids.includes(id)),
                    );
                  }}
                />
                <span>
                  <strong>{o.label}</strong>
                  <small>
                    {o.detail}
                    {!o.ids.length ? " · No members" : ""}
                  </small>
                </span>
              </label>
            );
          })}
          {!matches.length && <p>No matching records.</p>}
        </div>
      </details>
      {error && <ErrorBox error={error} />}
      <footer>
        <button
          className="button primary"
          disabled={busy || (!add.length && !remove.length)}
          onClick={() => void save()}
        >
          {busy ? "Saving…" : "Save assignments"}
          <Icon name="arrow" />
        </button>
      </footer>
    </div>
  );
}

export function ProgressHistory({
  path,
  manager = false,
}: {
  path: string;
  manager?: boolean;
}) {
  const resource = useResource<Progress[]>(path);
  return (
    <div className="detail-content">
      <State
        {...resource}
        retry={resource.refresh}
        empty={!resource.data?.length}
      >
        <div className="timeline">
          {resource.data?.map((p) => (
            <article key={p.id}>
              <div className="timeline-dot" />
              <div>
                <div className="timeline-title">
                  <Badge value={p.status} />
                  <time>{date(p.submitted_at)}</time>
                </div>
                {manager && (
                  <small>
                    Trainee #{p.trainee_id} · Plan #{p.plan_id}
                  </small>
                )}
                <p>{p.comments || "Status updated."}</p>
              </div>
            </article>
          ))}
        </div>
      </State>
    </div>
  );
}
