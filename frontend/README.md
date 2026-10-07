# Noticeboard frontend

React 18, TypeScript, and Vite, following the structure and authentication patterns of your Cognixia group project. Noticeboard has its own logo, colors, and training-focused screens.

## Run locally

From the repository root, start the backend in a terminal with your existing database password and JWT secret configured:

```powershell
.\.venv\Scripts\python -m uvicorn main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173/app. Node.js 20.19+ or 22+ is recommended. Vite forwards `/backend/*` requests to port 8000, stripping `/backend`. No database secrets belong in the frontend or any `VITE_*` variable.

Use your existing HR login. Signup creates a TRAINEE account. The person can find their user ID under **My account**; HR uses that ID to enroll them through **Add trainee**. A database admin still sets the first HR/Manager roles. No new migration is needed for the frontend; existing backend migrations and permissions still apply.

## Screens

- Everyone: signup, signin, sign out, read-only current account, own notifications and mark-read actions.
- HR: list/create/edit trainees, cohort assignment, list/create cohorts. Also read any learning plans assigned to their own trainee record.
- Manager: dashboard, trainee/cohort lists, create/edit/delete plans, assign to a trainee or cohort, review progress reports.
- Trainee: assigned plans, own report history, submit progress.

The backend remains the authority for roles and ownership. Hidden controls are only presentation. HTTP 401 clears the local session; 403, validation errors, network errors, rate limits, and empty lists have visible states. Expired tokens return the user to signin. There is no refresh-token endpoint, role editor, password-reset flow, or account editing API.

Cohort assignment applies to its current members, matching the backend. Moving a trainee into a cohort does not backfill its previous plan assignments. HR enrollment uses a user ID because the backend does not expose a user directory.

## Build and test

```powershell
npm run build
npx playwright install chromium
npm test
```

Browser tests run on port 5174 and mock API responses: they cover signup/signin, all three roles, plan editing and assignment, protected deletion, progress submission, notifications, logout, mobile navigation, retry, 401, and 429. Their sample people and records exist only in tests, never as production fallback data. The test screenshots are written under `test-results/` (gitignored). These tests do not establish connectivity to your EC2 database.

The production build is `dist/`. Serve its files with an SPA fallback to `index.html` for `/app/*`, and reverse-proxy `/backend/*` to FastAPI with that prefix removed. `npm run preview` only previews static files; it is not a production server. If using `VITE_API_URL`, it is public build-time configuration and a different origin needs backend CORS configuration. No deployment configuration was changed.

## Reused code and AI-written code to review

Source project: `C:\becloudready\repo\cognixia_jump_citi_full_stack_react_28_sep_group_2`, its `frontend/src` directory. This inventory describes reuse, not a claim about who originally authored every line in that project.

| Files | Provenance and changes |
| --- | --- |
| `src/auth/useAuth.ts`, `src/auth/usePathname.ts`, `src/types/auth.ts` | Reused from your project, with formatting changes. |
| `src/auth/authStore.ts` | Reused; storage key and change-event name changed to Noticeboard so the apps do not share sessions. |
| `src/api/client.ts` | Adapted from your client: retains bearer tokens, timeout, error parsing, 401 clearing and 429 messages. New Noticeboard service wording, `/backend` base path, and PUT helper. |
| `src/hooks.ts` | New resource-loading and expiry code. Inspired by your session-expiry hook, but does not attempt token refresh because this backend has no refresh route. |
| `src/App.tsx`, `src/components/*`, `src/pages/*` | New AI-written React components and business forms. Sidebar, authenticated shell, separate auth screens, and role navigation take inspiration from your project; markup and Noticeboard workflows are new. Review request bodies, role visibility, and user-facing wording. |
| `src/styles.css`, `public/favicon.svg`, `index.html` | New branding, responsive styling and logo. No Polis logo/assets copied. Fonts use Google Fonts with local fallbacks. |
| `src/types/models.ts`, `src/main.tsx`, Vite/TypeScript/package configuration, tests, this README | New setup, API types, browser tests, and documentation. |
| Backend changes in `services/{trainee,cohort,plan,progress,notification}_service.py` | New `RealDictCursor` use for list readers, so JSON contains field names instead of column-position arrays. Trainee list now joins the existing user/cohort tables for name, email and cohort name. Existing authorization and write permissions stay in force. Review this response-shape change if another client consumes those lists. |

`backend/tests/test_list_records.py` is also new AI-written coverage of the named-record cursor contract; it uses connection doubles and does not execute SQL against PostgreSQL.

The auth store intentionally retains your project's localStorage bearer-token approach. The API validates the token and current role on every request. Review that storage choice before production; a script running on the origin can read localStorage. Nothing here grants HR the ability to create HR or Manager accounts.
