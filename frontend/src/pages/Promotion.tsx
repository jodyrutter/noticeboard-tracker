import { useState } from "react";
import { api } from "../api/client";
import { useResource } from "../hooks";
import type { User } from "../types/models";
import { Badge, Modal, RecordForm, Search, State } from "../components/UI";

export function Promotion({ user }: { user: User }) {
  const resource = useResource<{ staff: User[]; eligible: User[] }>(
    "/users/promotion",
  );
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<User | null>(null);
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">WORKSPACE ACCESS</span>
          <h1>Promotion</h1>
          <p>
            Manage HR and Manager roles for people without assigned training.
          </p>
        </div>
        <button className="button" onClick={resource.refresh}>
          Refresh users
        </button>
      </div>
      <Search
        value={query}
        onChange={setQuery}
        placeholder="Search users by name or email…"
      />
      <State {...resource} retry={resource.refresh}>
        {(
          [
            { key: "staff", title: "Existing HR and Managers" },
            { key: "eligible", title: "Eligible trainees" },
          ] as const
        ).map((group) => {
          const rows =
            resource.data?.[group.key].filter((u) =>
              `${u.name} ${u.email}`
                .toLowerCase()
                .includes(query.toLowerCase()),
            ) ?? [];
          return (
            <section key={group.key} className="promotion-section">
              <h2>{group.title}</h2>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Email</th>
                      <th>Role</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((u) => (
                      <tr key={u.user_id}>
                        <td>{u.name}</td>
                        <td>{u.email}</td>
                        <td>
                          <Badge value={u.role} />
                        </td>
                        <td>
                          <button
                            className="text-button"
                            aria-label={`Change role for ${u.email}`}
                            disabled={u.user_id === user.user_id}
                            onClick={() => setSelected(u)}
                          >
                            Change role
                          </button>
                          {u.user_id === user.user_id && (
                            <small className="muted">
                              Your account — another HR user must change your
                              role.
                            </small>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!rows.length && (
                  <p className="panel-note">No matching users.</p>
                )}
              </div>
            </section>
          );
        })}
      </State>
      {selected && selected.user_id !== user.user_id && (
        <Modal
          title={`Change role: ${selected.email}`}
          close={() => setSelected(null)}
        >
          <RecordForm
            fields={[
              {
                name: "role",
                label: "Account role",
                value: selected.role,
                required: true,
                options: [
                  { value: "TRAINEE", label: "Trainee" },
                  { value: "HR", label: "HR" },
                  { value: "MANAGER", label: "Manager" },
                ],
              },
            ]}
            label="Save role"
            submit={(v) =>
              api.patch(`/users/${selected.user_id}/role`, { role: v.role })
            }
            done={() => {
              setSelected(null);
              resource.refresh();
            }}
          />
        </Modal>
      )}
    </>
  );
}
