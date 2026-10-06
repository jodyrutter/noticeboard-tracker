# noticeboard-tracker
Noticeboard project for Cognixia Training

The backend now uses FastAPI. The existing PostgreSQL service functions and SQL
are reused unchanged. There is no frontend yet.

Auth is implemented with signup, signin, logout, and current-user endpoints.
See [auth setup and statement provenance](AUTH_REVIEW.md) for the required DB
migration, secret configuration, reused/new code, and proposed access rules.

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
checks all 15 original endpoints, auth, argument forwarding, validation,
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
- Extra request fields are ignored, consistent with the old handler reading only
  named fields. No new status enum, date-order rule, or positive-ID rule was added.

Existing business endpoints still have no authorization restrictions. Their
database connection cleanup on exceptions, pooling, and database error mapping
remain unchanged. Auth storage does use transaction/connection cleanup. The full
schema is absent; the new auth migration is in `backend/migrations`. In particular,
marking an unknown notification read still returns success, as before. CORS can
be configured once the frontend's origin is known.

Framework references: [FastAPI request models](https://fastapi.tiangolo.com/tutorial/body/)
and [Mangum adapter](https://mangum.fastapiexpert.com/adapter/).
