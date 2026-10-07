# noticeboard-tracker
Noticeboard project for Cognixia Training

The backend uses FastAPI and PostgreSQL, reusing the original service functions
with ownership checks for trainee actions. The React + TypeScript frontend is in
`frontend/`; see [frontend setup and code provenance](frontend/README.md).

Auth is implemented with signup, signin, logout, and current-user endpoints.
The auth tables are created by `backend/migrations/001_auth.sql`. The backend
requires `PG_PASSWORD` and a persistent random `NOTICEBOARD_JWT_SECRET` of at
least 32 bytes. For multiple workers or Lambda instances, set
`NOTICEBOARD_RATE_LIMIT_STORAGE_URI` to shared Redis storage; otherwise rate
limits are process-local. Signup always creates a TRAINEE user; a DB admin sets
the first HR/Manager roles.

## AWS deployment

See [deploy/README.md](deploy/README.md) for same-origin HTTPS, Nginx, the managed FastAPI service and the update script. Production React calls `/backend` on its own HTTPS host; FastAPI listens only on loopback HTTP.

## Roles and permissions

All business endpoints require a valid login. Missing/expired/revoked tokens
return 401; roles without permission return 403. Permissions use the current
database role on every request. HR is not a superuser.

| Endpoint | Allowed roles and scope |
| --- | --- |
| `GET /users/unenrolled` | HR only; trainee-role users without a trainee record. Returns user_id, name, email. |
| `GET /trainees`, `GET /cohorts` | HR and MANAGER; managers need assignment targets. |
| `GET /trainees/{trainee_id}`, `GET /cohorts/{cohort_id}` | HR/MANAGER, or the user linked to that trainee/cohort. Missing or inaccessible records return 404. |
| `POST /trainees` | HR; enroll an existing user whose role is TRAINEE. |
| `PATCH /trainees/{trainee_id}` | HR; edit status, onboarding date, or cohort. |
| `PUT /trainees/{trainee_id}` | HR; replace all three editable trainee fields. |
| `POST /cohorts` | HR. |
| `GET /plans` | MANAGER: all plans. Other authenticated users: only plans assigned to their trainee records. |
| `GET /plans/{plan_id}` | MANAGER: any plan. Other authenticated users: an assigned plan only; otherwise 404. |
| `POST /plans` | MANAGER; creator is taken from the authenticated user. |
| `PUT /plans/{plan_id}` | MANAGER; replace title, description, and due date; original creator stays unchanged. |
| `DELETE /plans/{plan_id}` | MANAGER; 204 on deletion, 404 if missing, 409 if assignments or progress reference the plan. |
| `POST /plans/{plan_id}/assign/trainee/{trainee_id}` | MANAGER. |
| `POST /plans/{plan_id}/assign/cohort/{cohort_id}` | MANAGER. |
| `GET /progress/trainee/{trainee_id}` | MANAGER, or the user who owns that trainee record. Other users receive 404. |
| `GET /progress/plan/{plan_id}` | MANAGER sees all reports. An assigned user sees only their own reports. Inaccessible/missing plans return 404. |
| `GET /dashboard`, `GET /dashboard/trainees` | MANAGER. |
| `POST /progress` | TRAINEE; the supplied trainee ID must belong to the signed-in user and the plan must be assigned to that trainee. |
| `GET /notifications/{user_id}` | Any authenticated role; only their own user ID. |
| `PUT /notifications/{notification_id}/read` | Any authenticated role; only their own notification. Missing/other users' notifications return 404. |
| `POST /notifications` | Disabled for all MVP roles (403); no creation permission was specified. |

Signup/login remain public and rate limited. `/api/me` and `/api/logout` remain
available to every authenticated role. Docs remain public locally and are disabled when NOTICEBOARD_ENV=production. There are no
public role-promotion or HR/Manager signup endpoints. HR can manage roles through
`GET /users/promotion` and `PATCH /users/{user_id}/role`.

For trainee edits, run `backend/migrations/002_trainee_edit_permissions.sql` as a
DB admin if the app user does not already have UPDATE permission. No new tables
or columns are required for role enforcement. Example HR requests:

```http
PATCH /trainees/7
Content-Type: application/json
Authorization: Bearer <HR token>

{"cohort_id": 2}
```

The same endpoint accepts `status` and `onboarding_date` in any combination.
`cohort_id: null` removes a cohort assignment; omitted fields stay unchanged.
It cannot change `user_id`, roles, passwords, names, or emails. Unknown fields,
empty edits, and null status/onboarding dates return 422. A missing trainee
returns 404 and an invalid cohort returns 400. Signup creates the user account;
HR creates its trainee record separately using `POST /trainees`.

Plan creation now rejects `created_by` in the request body. Progress submission
takes `plan_id`, `status`, and `comments`. An optional `trainee_id` is checked
against the authenticated user; if omitted, the backend resolves their trainee
record. Multiple matching records return 409 instead of guessing. Ownership and
assignment are checked again within the INSERT. Changing a cohort does not remove existing
plan assignments or automatically assign that cohort's previous plans.

The role dependencies, edit endpoint, ownership SQL, permission tests, and DB
grant are new AI-written changes. Existing service logic is reused where possible.

The added detail, PUT, delete, and progress-by-plan services and tests are also
AI-written; trainee PUT reuses the existing update service. The single-record GET
endpoints return JSON objects with named fields. List/progress endpoints now
return arrays of named objects for the React frontend, rather than positional arrays.

`PUT /trainees/{trainee_id}` requires `cohort_id`, `status`, and `onboarding_date`.
`PUT /plans/{plan_id}` requires `title`, `description`, and `due_date`.
Nullable fields must still be supplied explicitly (use JSON null to clear them).
Neither PUT creates a missing record or changes its owning user/creator.
The existing trainee PATCH remains available for partial edits.

Run `backend/migrations/003_plan_edit_permissions.sql` as a DB admin if the app
user does not already have the plan UPDATE/DELETE privileges. Deletion checks
assignments and reports before deleting and does not cascade away training history.

## Run locally (PowerShell)

From the repository root, using Python 3.10 or newer:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.txt
$env:PG_PASSWORD = "your-database-password"
$env:NOTICEBOARD_JWT_SECRET = "your-persistent-random-secret-at-least-32-bytes"
.\.venv\Scripts\python -m uvicorn main:app --app-dir backend --reload
```

Open http://127.0.0.1:8000/docs to inspect and try the endpoints.
OpenAPI is at http://127.0.0.1:8000/openapi.json.
The interactive docs make real database changes when you submit write requests.
Database host, name, user, and port still come from `backend/database.py`.
The server and docs can start without database access; data endpoints require it.

## Tests

```powershell
.\.venv\Scripts\python -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python -m pytest -q
```

The automated suite mocks service calls and blocks PostgreSQL connections. It
checks the business endpoints, the role/anonymous access matrix, auth, argument forwarding, validation,
serialization, docs, and the Lambda adapter. It does not verify SQL against the actual schema.
The original `backend/test_database.py`, `test_trainee_service.py`, and
`test_lambda.py` remain manual scripts and only execute when run directly.
The first two insert records into the configured database.

## AWS Lambda

`backend/lambda_function.py` now wraps the same FastAPI application with Mangum.
When packaging the contents of `backend` at the deployment root, keep the handler
name `lambda_function.lambda_handler`. Include the runtime requirements built
for Lambda's Python version, Linux platform, and CPU architecture; the local
Windows virtual environment cannot be deployed as a Lambda dependency bundle.
The adapter test uses an API Gateway HTTP API v2 event, matching the original
handler's event format. No AWS configuration was changed or deployed.

## AI-assisted migration: review guide

All new migration code, tests, and these instructions were AI-written or adapted
from the original handler. This is an inventory of this change, not a claim about
the authorship of pre-existing code.

| File | What to review |
| --- | --- |
| `backend/main.py` | FastAPI routes replacing the manual routing. Service calls, argument order, success codes, and messages follow the original handler. |
| `backend/schemas.py` | New request types inferred from existing calls. Check these against your database and intended forms. All fields remain required; cohort ID, end date, description, due date, and comments accept explicit null. Dates are parsed into Python dates. Trainee and progress status values use the explicit enums described below. |
| `backend/lambda_function.py` | New Mangum adapter preserving the handler name. Verify in your actual AWS environment before deployment. |
| `backend/tests/test_api.py`, `pytest.ini` | New mocked HTTP tests and test-discovery configuration. These verify routing, not database correctness. |
| `backend/test_*.py` | Existing manual scripts wrapped in main guards; the Lambda sample now supplies a full HTTP API v2 event. |
| `backend/requirements*.txt` | Added framework, server, adapter, and test dependencies with version ranges. |

Intentional API differences to review:

- Missing or incorrectly typed inputs return FastAPI's HTTP 422 validation errors.
- Unknown routes use FastAPI's 404 JSON body; unsupported methods return 405.
- Paths are matched exactly instead of the old prefix/substring matching.
- Datetimes serialize as ISO 8601 with `T` between date and time rather than the
  old `str(datetime)` space. Dates remain `YYYY-MM-DD`; list records now use named objects.
- Trainee creation/updates, plan creation, progress submission, and auth reject
  extra fields. Status values are restricted to the enums below. No date-order or positive-ID rule was added.

The full schema is absent from the repository; SQL checks need verification
against the deployed database. Existing unchanged services still need broader
connection cleanup/error mapping improvements. Auth and modified ownership-write
services use transaction/connection cleanup. The local frontend uses a same-origin
Vite proxy to the backend; production needs an equivalent reverse proxy.

Framework references: [FastAPI request models](https://fastapi.tiangolo.com/tutorial/body/)
and [Mangum adapter](https://mangum.fastapiexpert.com/adapter/).

Ownership access is implemented on the existing ID-based routes. No new
`/api/me/...` routes or `PATCH /api/me` were added; the original `GET /api/me`
remains the current-user lookup. Trainee IDs are checked against `trainees.user_id`,
not compared directly with the user ID. Staff write permissions are unchanged.
The ownership-query helpers and associated tests are new AI-written code.


HR enrollment now uses a searchable, scrollable email picker populated by
`GET /users/unenrolled`. The existing `POST /trainees` still accepts `user_id`;
the frontend resolves it from the selected email. The endpoint excludes all
users with an existing trainee record, including inactive records, and excludes
HR/Manager accounts. It exposes only ID, name and email, never password hashes.
Duplicate enrollment returns 409. Enrollment requests take a transaction-level
advisory lock per user before checking for an existing record, preventing two
requests through this service from enrolling the same user concurrently. Direct
SQL writers must enforce the same rule separately. No schema migration is needed.
The endpoint, query, duplicate guard, email picker and related tests are new
AI-written code; they reuse existing HR authorization and enrollment forms.


## Status values and Promotion

Trainee status: `ACTIVE`, `INACTIVE`, `COMPLETED`, `WITHDRAWN`.
Progress status: `NOT_STARTED`, `IN_PROGRESS`, `COMPLETED`, `BLOCKED`.
Create, PUT and PATCH validation use these exact, case-sensitive values (422 on
invalid input), and the frontend provides matching selects. Dashboard report
counts include NOT_STARTED reports separately from assignments without reports.

HR can open **Promotion** (`/app/promotion`). `GET /users/promotion` returns
`staff` (all HR/Managers) and `eligible` (TRAINEE accounts with no plan assignments
across any of their trainee profiles). An existing trainee profile or cohort
membership alone does not exclude someone. Completed plan assignments still count
as assignments. Both lists include only public account fields. Both this route
and `PATCH /users/{user_id}/role` require HR. Role changes accept TRAINEE, HR or
MANAGER, recheck assignments, and return 409 if training is assigned. Users can
return to TRAINEE without losing their existing profile. Users cannot change their own role. Their Promotion action is disabled, and
the API returns 403 before calling the update service. Another HR user must
make the role change.

Run `backend/migrations/004_status_values_and_promotion.sql` once as a DB admin.
It adds CHECK constraints for the two status fields and grants the app user
UPDATE permission on users.role. Existing invalid/null statuses cause validation
to fail and the transaction to roll back; correct those deliberately before
rerunning. No records are automatically renamed/deleted. Promotion eligibility is
an application check; no database eligibility constraint or trigger is added.
This assumes staff do not receive training assignments, as requested.

The status definitions, Promotion service/routes/page, SQL script, dashboard
NOT_STARTED count, and added tests are new AI-written code using the existing
HR dependency, account roles, service connection patterns and shared forms.


Managers can now read and edit saved plan assignments using GET/PATCH
`/plans/{plan_id}/assignments`. PATCH takes `add` and `remove` lists of trainee
IDs, changes only these links in a transaction, and preserves progress reports.
Existing assignments are prechecked in the UI and can be unchecked. Apply
`backend/migrations/005_assignment_removal_permissions.sql` as a DB admin to
allow the application to delete assignment links. This service, schema, UI
change, permission script and tests are new AI-written code.

The self-role-change guard and its UI/API tests are new AI-written changes.


See [business workflow and deployment readiness](DEPLOYMENT_READINESS.md) for
the new automatic in-app notifications, Manager tracking API, migration 006,
local acceptance walkthrough, and remaining AWS release checks.
