# noticeboard-tracker
Noticeboard project for Cognixia Training

The backend uses FastAPI and PostgreSQL, reusing the original service functions
with ownership checks for trainee actions. There is no frontend yet.

Auth is implemented with signup, signin, logout, and current-user endpoints.
The auth tables are created by `backend/migrations/001_auth.sql`. The backend
requires `PG_PASSWORD` and a persistent random `NOTICEBOARD_JWT_SECRET` of at
least 32 bytes. For multiple workers or Lambda instances, set
`NOTICEBOARD_RATE_LIMIT_STORAGE_URI` to shared Redis storage; otherwise rate
limits are process-local. Signup always creates a TRAINEE user; a DB admin sets
the first HR/Manager roles.

## Roles and permissions

All business endpoints require a valid login. Missing/expired/revoked tokens
return 401; roles without permission return 403. Permissions use the current
database role on every request. HR is not a superuser.

| Endpoint | Allowed roles and scope |
| --- | --- |
| `GET /trainees`, `GET /cohorts` | HR and MANAGER; managers need assignment targets. |
| `POST /trainees` | HR; enroll an existing user whose role is TRAINEE. |
| `PATCH /trainees/{trainee_id}` | HR; edit status, onboarding date, or cohort. |
| `POST /cohorts` | HR. |
| `GET /plans` | MANAGER: all plans. TRAINEE: only plans assigned to their trainee records. |
| `POST /plans` | MANAGER; creator is taken from the authenticated user. |
| `POST /plans/{plan_id}/assign/trainee/{trainee_id}` | MANAGER. |
| `POST /plans/{plan_id}/assign/cohort/{cohort_id}` | MANAGER. |
| `GET /progress/trainee/{trainee_id}` | MANAGER. |
| `GET /dashboard`, `GET /dashboard/trainees` | MANAGER. |
| `POST /progress` | TRAINEE; the supplied trainee ID must belong to the signed-in user and the plan must be assigned to that trainee. |
| `GET /notifications/{user_id}` | TRAINEE; only their own user ID. |
| `PUT /notifications/{notification_id}/read` | TRAINEE; only their own notification. Missing/other users' notifications return 404. |
| `POST /notifications` | Disabled for all MVP roles (403); no creation permission was specified. |

Signup/login remain public and rate limited. `/api/me` and `/api/logout` remain
available to every authenticated role. Docs remain public. There are no
role-promotion or HR/Manager creation endpoints.

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
still takes `trainee_id`, `plan_id`, `status`, and `comments`, but checks ownership
and assignment within the INSERT. Changing a cohort does not remove existing
plan assignments or automatically assign that cohort's previous plans.

The role dependencies, edit endpoint, ownership SQL, permission tests, and DB
grant are new AI-written changes. Existing service logic is reused where possible.

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
| `backend/schemas.py` | New request types inferred from existing calls. Check these against your database and intended forms. All fields remain required; cohort ID, end date, description, due date, and comments accept explicit null. Dates are parsed into Python dates. Status values remain unrestricted strings because the schema is unavailable. |
| `backend/lambda_function.py` | New Mangum adapter preserving the handler name. Verify in your actual AWS environment before deployment. |
| `backend/tests/test_api.py`, `pytest.ini` | New mocked HTTP tests and test-discovery configuration. These verify routing, not database correctness. |
| `backend/test_*.py` | Existing manual scripts wrapped in main guards; the Lambda sample now supplies a full HTTP API v2 event. |
| `backend/requirements*.txt` | Added framework, server, adapter, and test dependencies with version ranges. |

Intentional API differences to review:

- Missing or incorrectly typed inputs return FastAPI's HTTP 422 validation errors.
- Unknown routes use FastAPI's 404 JSON body; unsupported methods return 405.
- Paths are matched exactly instead of the old prefix/substring matching.
- Datetimes serialize as ISO 8601 with `T` between date and time rather than the
  old `str(datetime)` space. Dates remain `YYYY-MM-DD`; row tuples remain arrays.
- Trainee creation/updates, plan creation, progress submission, and auth reject
  extra fields. No new status enum, date-order rule, or positive-ID rule was added.

The full schema is absent from the repository; SQL checks need verification
against the deployed database. Existing unchanged services still need broader
connection cleanup/error mapping improvements. Auth and modified ownership-write
services use transaction/connection cleanup. CORS can be configured once the
frontend's origin is known.

Framework references: [FastAPI request models](https://fastapi.tiangolo.com/tutorial/body/)
and [Mangum adapter](https://mangum.fastapiexpert.com/adapter/).
