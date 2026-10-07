import {
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
  type FormEvent,
} from "react";

export function Logo() {
  return (
    <span className="wordmark">
      <span className="brand-mark">
        n<span />
      </span>
      noticeboard<span className="brand-dot">.</span>
    </span>
  );
}
export function Icon({ name }: { name: string }) {
  const paths: Record<string, ReactNode> = {
    overview: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </>
    ),
    plans: (
      <>
        <rect x="4" y="3" width="16" height="18" rx="2" />
        <path d="M8 8h8M8 12h8M8 16h5" />
      </>
    ),
    trainees: (
      <>
        <circle cx="9" cy="8" r="3" />
        <path d="M3 21v-3a6 6 0 0 1 12 0v3M17 5a3 3 0 0 1 0 6M18 15a5 5 0 0 1 3 6" />
      </>
    ),
    cohorts: (
      <>
        <rect x="3" y="5" width="18" height="16" rx="2" />
        <path d="M7 3v5M17 3v5M3 11h18M8 15h2M14 15h2" />
      </>
    ),
    notifications: (
      <>
        <path d="M18 8a6 6 0 0 0-12 0c0 8-3 8-3 10h18c0-2-3-2-3-10M10 22h4" />
      </>
    ),
    profile: (
      <>
        <circle cx="12" cy="8" r="4" />
        <path d="M4 22v-2a8 8 0 0 1 16 0v2" />
      </>
    ),
    arrow: <path d="M5 12h14m-5-5 5 5-5 5" />,
    search: (
      <>
        <circle cx="10" cy="10" r="6" />
        <path d="m15 15 6 6" />
      </>
    ),
  };
  return (
    <svg
      aria-hidden="true"
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name] ?? paths.plans}
    </svg>
  );
}
export function Badge({ value }: { value: string }) {
  return (
    <span className={`badge ${value.toLowerCase().replaceAll("_", "-")}`}>
      {value.replaceAll("_", " ").toLowerCase()}
    </span>
  );
}
export function date(value: string | null | undefined) {
  if (!value) return "No date set";
  const d = new Date(value.length === 10 ? `${value}T12:00:00` : value);
  return Number.isNaN(d.getTime())
    ? "—"
    : d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
}
export function ErrorBox({
  error,
  retry,
}: {
  error: string;
  retry?: () => void;
}) {
  return (
    <div className="error-box" role="alert">
      <span>{error}</span>
      {retry && (
        <button className="text-button" onClick={retry}>
          Try again
        </button>
      )}
    </div>
  );
}
export function State({
  loading,
  error,
  retry,
  empty,
  children,
}: {
  loading: boolean;
  error: string;
  retry: () => void;
  empty?: boolean;
  children: ReactNode;
}) {
  if (loading)
    return (
      <div className="loading" role="status">
        <span className="spinner" />
        Loading your workspace…
      </div>
    );
  if (error) return <ErrorBox error={error} retry={retry} />;
  if (empty)
    return (
      <div className="empty">
        <Icon name="plans" />
        <h3>Nothing here yet</h3>
        <p>New records will appear here when they’re added.</p>
      </div>
    );
  return <>{children}</>;
}
export function Modal({
  title,
  close,
  children,
}: {
  title: string;
  close: () => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement;
    ref.current?.showModal();
    return () => {
      previous?.focus();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      onCancel={(e) => {
        e.preventDefault();
        close();
      }}
    >
      <header>
        <div>
          <span className="eyebrow">NOTICEBOARD WORKSPACE</span>
          <h2>{title}</h2>
        </div>
        <button
          className="icon-button"
          aria-label="Close dialog"
          onClick={close}
        >
          ×
        </button>
      </header>
      {children}
    </dialog>
  );
}
export interface Field {
  name: string;
  label: string;
  type?: string;
  value?: string | number | null;
  required?: boolean;
  options?: { value: string | number; label: string }[];
  hint?: string;
  maxLength?: number;
}
export function RecordForm({
  fields,
  submit,
  label = "Save changes",
  done,
}: {
  fields: Field[];
  submit: (values: Record<string, string>) => Promise<unknown>;
  label?: string;
  done: () => void;
}) {
  const formId = useId();
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy) return;
    const values = Object.fromEntries(new FormData(e.currentTarget)) as Record<
      string,
      string
    >;
    setBusy(true);
    setError("");
    try {
      await submit(values);
      done();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form onSubmit={save} className="record-form">
      {fields.map((f) => (
        <label className="field" key={f.name}>
          <span id={`${formId}-${f.name}-label`}>{f.label}</span>
          {f.type === "textarea" ? (
            <textarea
              aria-labelledby={`${formId}-${f.name}-label`}
              aria-describedby={f.hint ? `${formId}-${f.name}-hint` : undefined}
              name={f.name}
              defaultValue={f.value ?? ""}
              required={f.required}
              maxLength={f.maxLength}
              rows={4}
            />
          ) : f.options ? (
            <select
              aria-labelledby={`${formId}-${f.name}-label`}
              aria-describedby={f.hint ? `${formId}-${f.name}-hint` : undefined}
              name={f.name}
              defaultValue={f.value ?? ""}
              required={f.required}
            >
              <option value="">Choose…</option>
              {f.options.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          ) : (
            <input
              aria-labelledby={`${formId}-${f.name}-label`}
              aria-describedby={f.hint ? `${formId}-${f.name}-hint` : undefined}
              name={f.name}
              type={f.type ?? "text"}
              defaultValue={f.value ?? ""}
              required={f.required}
              maxLength={f.maxLength}
              min={f.type === "number" ? 1 : undefined}
            />
          )}{" "}
          {f.hint && <small id={`${formId}-${f.name}-hint`}>{f.hint}</small>}
        </label>
      ))}
      {error && <ErrorBox error={error} />}
      <footer>
        <button className="button primary" disabled={busy}>
          {busy ? "Saving…" : label}
          <Icon name="arrow" />
        </button>
      </footer>
    </form>
  );
}
export function Search({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (s: string) => void;
  placeholder: string;
}) {
  return (
    <label className="search">
      <Icon name="search" />
      <input
        aria-label={placeholder}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}
