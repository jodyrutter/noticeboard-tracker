# Auth implementation and statement provenance

Reference project: `C:\becloudready\repo\cognixia_jump_citi_full_stack_react_28_sep_group_2`.
Its files were read only. No frontend was added.

The table below identifies **REUSED**, **ADAPTED**, and **NEW** code. Reused means
statements copied from that repository, not independent verification of their
original author. Adapted means I changed statements to fit this project: treat
those changes as AI-written. Everything not explicitly identified as reused is
new or adapted AI-written code, including tests, SQL, configuration, and docs.

| Noticeboard code | Source and provenance |
| --- | --- |
| `backend/auth_models.py`: `_validate_password_strength`, `_validate_email_format`, constants, validator method bodies | REUSED from banking `app/models.py`. Same minimum 8 characters and at least one non-alphanumeric character; same email regex. |
| `backend/auth_models.py`: request and response classes | ADAPTED from `CustomerCreate`, `LoginRequest`, `User`, and `Me`. NEW bounds, password `repr=False`, roles, forbidden extra auth fields, and nullable-free signup. Password whitespace is preserved instead of stripped. Address is omitted because noticeboard users do not have an address in the visible SQL. |
| `backend/auth.py`: `authentication_error`, algorithm/lifetime/bearer declarations | REUSED from banking `app/auth.py`. |
| `backend/auth.py`: token creation/decoding, current user, logout | ADAPTED from the same file: same HS256 JWT claims (`sub`, `username`, `role`, `sid`, `jti`, `exp`) and 30-minute lifetimes. NEW environment name/minimum secret length, database session calls, integer bounds, and current DB role lookup. |
| `backend/services/auth_service.py` | NEW PostgreSQL queries, connection/transaction management and session storage. Hash/verify statements and duplicate-email exception pattern are ADAPTED from banking `MongoUserStore`. NEW dummy hash for unknown email checks and invalid legacy hash handling. |
| `backend/auth_routes.py`: `rate_limit_exceeded_handler` | REUSED from banking `app/main.py`. |
| `backend/auth_routes.py`: endpoint bodies and limiter setup | ADAPTED from banking signup, `_login`, logout, `/api/me`, and SlowAPI setup. Same login response and error messages. NEW single login URL, Redis configuration, logout/me limits, pre-validation rate-limit wrapper, and no-store response headers. |
| `backend/main.py`: auth wiring and validation handler | ADAPTED limiter registration; NEW router inclusion and redaction of input/context from auth validation errors so passwords are not echoed. Existing business routes keep their original access behavior. |
| `backend/migrations/001_auth.sql` | Entirely NEW. Adds session storage, role default, normalized email uniqueness, indexes, and session-table permissions. |
| `backend/tests/test_auth.py` and auth additions to API tests | Entirely NEW. These are not tests copied from the other project. |

## API behavior

| Method and path | Request / response | Per-client-IP limit |
| --- | --- | --- |
| `POST /api/signup` | `{ "name": "Alex", "email": "alex@example.com", "password": "Example!123" }` → 201 with `user_id`, `name`, `email`, `role` | 3/minute |
| `POST /api/login` | Email/password → `access_token` and `token_type: "bearer"` | 5/minute |
| `GET /api/me` | Bearer token → current user and DB role | 60/minute |
| `POST /api/logout` | Bearer token → 204, revokes that login session | 30/minute |

Signup does not automatically sign in, matching your banking project. All roles
use the same signin endpoint. Send `Authorization: Bearer <access_token>` to me
and logout. Swagger's Authorize button accepts the token. The future frontend
should discard its saved token after logout or a 401 response.

Only signup can create users through this API, and its SQL always inserts
`TRAINEE`. A request containing `role`, `admin`, or other extra fields is rejected.
The role default also covers DB inserts that omit role. This is a user role, not
automatic creation of a `trainees` onboarding record: that requires cohort/status/
onboarding decisions. There is no public HR/Manager creation or promotion route.

JWTs expire after 30 minutes, and expired/idle/revoked sessions cannot authenticate.
No refresh endpoint was added in this scope, so a user signs in again on expiry.
Logout is session-specific; other devices stay signed in. Repeating logout with
the same still-unexpired JWT returns 204. Expired/invalid tokens return 401.
Existing placeholder passwords such as `temporary` are not valid password hashes.

## Database and configuration setup

The migration has **not** been applied to the remote database. The existing schema
is not in this repository. A DB admin should check `users` has `id`, `name`,
`email`, `password_hash`, and `role`, and that role permits `TRAINEE`, `HR`, and
`MANAGER`. `password_hash` must fit Argon2 encoded hashes (TEXT is suitable).
Other required columns must have defaults if they are not in the signup INSERT.

Run `backend/migrations/001_auth.sql` once as a DB admin against the noticeboard
database. It is transactional, and intentionally fails if normalized emails are
already duplicated. It does not merge users or change existing roles. The app
user needs its existing users-table SELECT/INSERT and sequence privileges; the
migration grants access to the new session table to `noticeboard_app`.

Set `NOTICEBOARD_JWT_SECRET` to a persistent, random secret of at least 32 bytes.
Generate one locally with `python -c "import secrets; print(secrets.token_urlsafe(48))"`
and store it in your deployment's secret configuration. Use the same secret on
every worker/Lambda instance. Missing/short secrets return 503 from signup/login
without writing a user. Do not reuse the banking JWT secret.

Set `NOTICEBOARD_RATE_LIMIT_STORAGE_URI` to your shared Redis URI for Lambda or
multiple workers, for example `redis://localhost:6379/0` for local Redis. Without
it, the limiter uses process-local memory, as the banking project does. That mode
is only suitable for single-process development: restarts reset counts and
multiple processes do not share limits. Configured storage failures do not silently
fall back to memory. Redis connectivity still needs validation in deployment.

Rate limiting uses the actual ASGI client address, not arbitrary forwarded
headers. For reverse-proxy deployments, configure the ASGI server to trust only
the real proxy IPs; API Gateway v2 supplies the client address through Mangum.
Users sharing a network share these limits. Invalid request bodies count too.

After a person signs up, a DB admin can promote that specific account, e.g.:

```sql
UPDATE users SET role = 'HR' WHERE id = <verified_user_id>;
-- Or use 'MANAGER'. This is an example, not executed by this change.
```

Current-user lookup reads the DB role on every request, so promotion/demotion is
reflected without trusting an older token's role claim. Expired session rows are
cleaned on login; a scheduled DB cleanup may be useful as usage grows.

## Suggested authorization (not implemented)

| Endpoints | Suggested policy |
| --- | --- |
| Trainee/cohort listing and dashboards | HR/Manager; trainees get an own-profile/progress view instead of the full roster. |
| Creating trainees and cohorts | HR; allow managers only if they handle onboarding. |
| Creating plans and assigning plans | HR/Manager; derive `created_by` from the signed-in user. |
| Submitting progress | Trainee for their own record and assigned plan; derive their trainee ID server-side. |
| Reading trainee progress | That trainee, HR, or an authorized Manager. |
| Reading/marking notifications | Only the recipient; derive or verify the user ID. |
| Creating notifications | HR/Manager or internal application logic. |
| Future role management | HR only, explicit HR/Manager allowlist, audit actor/target/old/new role, prevent removal of the last HR. Bootstrap the first privileged user through a DB admin. |

All 15 pre-existing business endpoints remain callable without a login, as
requested. Only the new `/api/me` and `/api/logout` require a bearer token.

## Verification boundaries

Automated tests exercise Argon2 hashing, required claims, expiry, tampering,
role-injection rejection, logout/replay behavior, current DB role changes,
normalization, validation redaction, and rate limiting before password work.
Service/database doubles avoid connecting to the remote database. SQL and actual
AWS/Redis integration must be checked after applying the migration in a test
environment. Existing business-route tests still verify anonymous access.

References consulted: [SlowAPI](https://slowapi.readthedocs.io/en/latest/),
[PyJWT](https://pyjwt.readthedocs.io/en/stable/usage.html),
[pwdlib](https://frankie567.github.io/pwdlib/reference/pwdlib/).
