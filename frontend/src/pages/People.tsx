import { useState } from "react";
import { api } from "../api/client";
import { useResource } from "../hooks";
import type { Cohort, Trainee, User } from "../types/models";
import {
  Badge,
  date,
  Icon,
  Modal,
  RecordForm,
  Search,
  State,
  type Field,
} from "../components/UI";
import { ProgressHistory } from "./Plans";

export function Trainees({ user }: { user: User }) {
  const resource = useResource<Trainee[]>("/trainees"),
    cohorts = useResource<Cohort[]>("/cohorts");
  const [search, setSearch] = useState(""),
    [create, setCreate] = useState(false),
    [selected, setSelected] = useState<Trainee | null>(null);
  const rows =
    resource.data?.filter((t) =>
      `${t.name} ${t.email} ${t.cohort_name ?? ""} ${t.id}`
        .toLowerCase()
        .includes(search.toLowerCase()),
    ) ?? [];
  const fields = (t?: Trainee): Field[] => [
    {
      name: "cohort_id",
      label: "Cohort (optional)",
      value: t?.cohort_id,
      options: cohorts.data?.map((c) => ({ value: c.id, label: c.name })) ?? [],
    },
    {
      name: "status",
      label: "Status",
      value: t?.status ?? "ACTIVE",
      required: true,
      options: ["ACTIVE", "INACTIVE", "COMPLETED", "WITHDRAWN"].map(
        (value) => ({ value, label: value }),
      ),
    },
    {
      name: "onboarding_date",
      label: "Onboarding date",
      type: "date",
      required: true,
      value: t?.onboarding_date?.slice(0, 10),
    },
  ];
  function body(v: Record<string, string>) {
    return {
      cohort_id: v.cohort_id ? Number(v.cohort_id) : null,
      status: v.status,
      onboarding_date: v.onboarding_date,
    };
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">PEOPLE AT THE CENTER</span>
          <h1>Trainees</h1>
          <p>Know your people. Help them take their next step.</p>
        </div>
        {user.role === "HR" && (
          <button className="button primary" onClick={() => setCreate(true)}>
            ＋ Add trainee
          </button>
        )}
      </div>
      <div className="toolbar">
        <Search
          value={search}
          onChange={setSearch}
          placeholder="Search name, email, or cohort…"
        />
        <span className="muted">{rows.length} people</span>
      </div>
      <State {...resource} retry={resource.refresh} empty={!rows.length}>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Trainee</th>
                <th>Cohort</th>
                <th>Onboarded</th>
                <th>Status</th>
                <th>
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((t) => (
                <tr key={t.id}>
                  <td>
                    <div className="person">
                      <span className="avatar">
                        {(t.name || "T").slice(0, 1)}
                      </span>
                      <div>
                        <strong>{t.name || `Trainee #${t.id}`}</strong>
                        <small>{t.email || `User #${t.user_id}`}</small>
                      </div>
                    </div>
                  </td>
                  <td>{t.cohort_name || "Not assigned"}</td>
                  <td>{date(t.onboarding_date)}</td>
                  <td>
                    <Badge value={t.status} />
                  </td>
                  <td>
                    <button
                      className="text-button"
                      onClick={() => setSelected(t)}
                    >
                      View <Icon name="arrow" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </State>
      {create && (
        <Modal title="Welcome a new trainee" close={() => setCreate(false)}>
          <State {...cohorts} retry={cohorts.refresh}>
            <EnrollTrainee
              fields={fields()}
              label="Add trainee"
              submit={(v) =>
                api.post("/trainees", {
                  ...body(v),
                  user_id: Number(v.user_id),
                })
              }
              done={() => {
                setCreate(false);
                resource.refresh();
              }}
            />
          </State>
        </Modal>
      )}
      {selected && (
        <Modal
          title={selected.name || `Trainee #${selected.id}`}
          close={() => setSelected(null)}
        >
          <div className="detail-meta padded">
            <span>
              User account<strong>#{selected.user_id}</strong>
            </span>
            <span>
              Trainee record<strong>#{selected.id}</strong>
            </span>
          </div>
          {user.role === "HR" ? (
            <State {...cohorts} retry={cohorts.refresh}>
              <RecordForm
                fields={fields(selected)}
                submit={(v) => api.patch(`/trainees/${selected.id}`, body(v))}
                done={() => {
                  setSelected(null);
                  resource.refresh();
                }}
              />
            </State>
          ) : (
            <ProgressHistory
              path={`/progress/trainee/${selected.id}`}
              manager
            />
          )}
        </Modal>
      )}
    </>
  );
}

function EnrollTrainee(props: React.ComponentProps<typeof RecordForm>) {
  const users =
    useResource<{ user_id: number; name: string; email: string }[]>(
      "/users/unenrolled",
    );
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState("");
  const matches =
    users.data?.filter((u) =>
      u.email.toLowerCase().includes(query.trim().toLowerCase()),
    ) ?? [];
  return (
    <State {...users} retry={users.refresh}>
      {!users.data?.length ? (
        <div className="empty">
          <h3>No users awaiting enrollment</h3>
          <p>New trainee accounts will appear here after signup.</p>
          <button className="button" onClick={users.refresh}>
            Refresh available users
          </button>
        </div>
      ) : (
        <RecordForm
          {...props}
          submit={async (values) => {
            if (
              !selected ||
              !matches.some((u) => String(u.user_id) === selected)
            ) {
              throw new Error(
                "Select an available email before adding a trainee.",
              );
            }
            return props.submit({ ...values, user_id: selected });
          }}
        >
          <label className="field">
            Search by email
            <input
              type="search"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setSelected("");
              }}
              placeholder="Type an email address…"
            />
          </label>
          <label className="field">
            <span id="available-users-label">Available trainee emails</span>
            <select
              className="enrollment-list"
              aria-labelledby="available-users-label"
              name="user_id"
              size={6}
              required
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
            >
              <option value="" disabled>
                Select an email…
              </option>
              {matches.map((u) => (
                <option key={u.user_id} value={u.user_id}>
                  {u.email} — {u.name}
                </option>
              ))}
            </select>
          </label>
          {!matches.length && (
            <p role="status">No available users match that email.</p>
          )}
          <p className="muted">
            {selected
              ? `Selected: ${matches.find((u) => String(u.user_id) === selected)?.email}`
              : "Select an email to enroll this person."}
          </p>
          <button
            type="button"
            className="text-button"
            onClick={() => {
              setSelected("");
              users.refresh();
            }}
          >
            Refresh available users
          </button>
        </RecordForm>
      )}
    </State>
  );
}

export function Cohorts({ user }: { user: User }) {
  const resource = useResource<Cohort[]>("/cohorts");
  const [create, setCreate] = useState(false),
    [search, setSearch] = useState(""),
    [selected, setSelected] = useState<Cohort | null>(null);
  const rows =
    resource.data?.filter((c) =>
      c.name.toLowerCase().includes(search.toLowerCase()),
    ) ?? [];
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">BETTER, TOGETHER</span>
          <h1>Cohorts</h1>
          <p>A shared start. Individual possibilities.</p>
        </div>
        {user.role === "HR" && (
          <button className="button primary" onClick={() => setCreate(true)}>
            ＋ Create cohort
          </button>
        )}
      </div>
      <div className="toolbar">
        <Search
          value={search}
          onChange={setSearch}
          placeholder="Search cohorts…"
        />
        <span className="muted">{rows.length} cohorts</span>
      </div>
      <State {...resource} retry={resource.refresh} empty={!rows.length}>
        <div className="plan-grid">
          {rows.map((c, i) => (
            <article className="cohort-card" key={c.id}>
              <div className={`cohort-banner tone-${i % 3}`}>
                <Icon name="cohorts" />
                <span>COHORT {String(c.id).padStart(2, "0")}</span>
              </div>
              <div className="cohort-body">
                <h2>{c.name}</h2>
                <p>
                  {date(c.start_date)} —{" "}
                  {c.end_date ? date(c.end_date) : "Open-ended"}
                </p>
                <button className="text-button" onClick={() => setSelected(c)}>
                  View cohort <Icon name="arrow" />
                </button>
              </div>
            </article>
          ))}
        </div>
      </State>
      {selected && (
        <Modal title={selected.name} close={() => setSelected(null)}>
          <div className="detail-content">
            <p>Training cohort #{selected.id}</p>
            <div className="detail-meta">
              <span>
                Starts<strong>{date(selected.start_date)}</strong>
              </span>
              <span>
                Ends<strong>{date(selected.end_date)}</strong>
              </span>
            </div>
            {user.role === "HR" ? (
              <CohortMembers cohort={selected} />
            ) : (
              <p className="muted">
                Assign a training plan to this cohort from the Training plans
                page.
              </p>
            )}
          </div>
        </Modal>
      )}
      {create && (
        <Modal title="Create a cohort" close={() => setCreate(false)}>
          <RecordForm
            fields={[
              { name: "name", label: "Cohort name", required: true },
              {
                name: "start_date",
                label: "Start date",
                type: "date",
                required: true,
              },
              { name: "end_date", label: "End date (optional)", type: "date" },
            ]}
            label="Create cohort"
            submit={(v) => {
              if (v.end_date && v.end_date < v.start_date)
                return Promise.reject(
                  new Error("End date must be on or after the start date."),
                );
              return api.post("/cohorts", {
                ...v,
                end_date: v.end_date || null,
              });
            }}
            done={() => {
              setCreate(false);
              resource.refresh();
            }}
          />
        </Modal>
      )}
    </>
  );
}

function CohortMembers({ cohort }: { cohort: Cohort }) {
  const resource = useResource<Trainee[]>("/trainees");
  return (
    <State {...resource} retry={resource.refresh}>
      {resource.data && (
        <CohortMemberForm
          key={cohort.id}
          cohort={cohort}
          trainees={resource.data}
        />
      )}
    </State>
  );
}

function CohortMemberForm({
  cohort,
  trainees,
}: {
  cohort: Cohort;
  trainees: Trainee[];
}) {
  const [baseline, setBaseline] = useState(() =>
    trainees.filter((t) => t.cohort_id === cohort.id).map((t) => t.id),
  );
  const [selected, setSelected] = useState(baseline);
  const [query, setQuery] = useState("");
  const [saved, setSaved] = useState(false);
  const matches = trainees.filter((t) =>
    `${t.name} ${t.email}`.toLowerCase().includes(query.toLowerCase()),
  );
  return (
    <RecordForm
      fields={[]}
      label="Save members"
      submit={async () => {
        const snapshot = [...selected];
        await api.patch(`/cohorts/${cohort.id}/members`, {
          add: snapshot.filter((id) => !baseline.includes(id)),
          remove: baseline.filter((id) => !snapshot.includes(id)),
        });
        setBaseline(snapshot);
        setSaved(true);
      }}
      done={() => {}}
    >
      <p>
        Select people to join this cohort. Unchecking a member removes them from
        this cohort. Selecting someone from another cohort moves them here.
      </p>
      <details className="member-picker">
        <summary>Choose members ({selected.length} selected)</summary>
        <Search
          value={query}
          onChange={setQuery}
          placeholder="Search members by name or email…"
        />
        <div className="member-options">
          {matches.map((t) => (
            <label className="member-option" key={t.id}>
              <input
                type="checkbox"
                checked={selected.includes(t.id)}
                onChange={(e) => {
                  setSaved(false);
                  setSelected((ids) =>
                    e.target.checked
                      ? [...ids, t.id]
                      : ids.filter((id) => id !== t.id),
                  );
                }}
              />
              <span>
                <strong>{t.name || t.email}</strong>
                <small>
                  {t.email}
                  {t.cohort_id && t.cohort_id !== cohort.id
                    ? ` · ${t.cohort_name || "Another cohort"}`
                    : ""}
                </small>
              </span>
            </label>
          ))}
          {!matches.length && <p>No matching trainees.</p>}
        </div>
      </details>
      {saved && (
        <p className="success-box" role="status">
          Cohort members saved.
        </p>
      )}
    </RecordForm>
  );
}
