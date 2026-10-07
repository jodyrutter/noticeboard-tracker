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
    ...(!t
      ? [
          {
            name: "user_id",
            label: "User account ID",
            type: "number",
            required: true,
            hint: "The trainee can find this in My account after signing up.",
          },
        ]
      : []),
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
      hint: "Use a status supported by your training program.",
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
            <RecordForm
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
            <p className="muted">
              {user.role === "HR"
                ? "Assign people to this cohort from the Trainees page."
                : "Assign a training plan to this cohort from the Training plans page."}
            </p>
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
