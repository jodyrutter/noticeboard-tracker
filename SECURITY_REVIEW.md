# Security review — 7 October 2026

The application has a reasonable MVP authorization foundation, but this is not a production security sign-off. This review covers the tracked FastAPI services, React source, dependency audits and local tests. It does not verify the live PostgreSQL schema/grants, EC2 operating system, security groups, TLS certificates, reverse proxy or Git history. No AWS resources or database records were changed.

## Existing controls reviewed

- Backend dependencies enforce roles; hiding frontend navigation is not the security boundary. HR manages onboarding, cohorts and promotion; Managers manage plans, assignments and dashboards. Managers currently have organization-wide access by design.
- Trainee reads and writes use ownership/assignment checks. Notification reads and updates require the owner. Public notification creation remains disabled. HR cannot change their own role.
- Signup always writes TRAINEE, regardless of client input. Passwords use Argon2. JWT verification specifies HS256, requires claims, checks expiration and verifies the database session on each protected request. Logout revokes the session. Current database roles override stale JWT role claims.
- Reviewed SQL values are parameterized. Dynamic trainee-update column names use a fixed allowlist and SQL identifiers. Reviewed React rendering uses escaped text; no unsafe HTML insertion or evaluated user code was found.
- Login/signup already have IP rate limits and login uses a generic invalid-credentials response. Signup still reveals an existing email through its 409 response.

## Changes made in this review

| Gap | Fix |
| --- | --- |
| Unlimited body size at the app layer | Reject request bodies over 65,536 bytes with 413 before parsing. Count streamed bytes too, so an absent or understated Content-Length cannot bypass the cap. A reverse proxy must still enforce timeouts and connection limits. |
| Unlimited repeated business writes | One shared 120-per-minute IP budget across registered business POST/PUT/PATCH/DELETE routes, including malformed and forbidden requests. Existing tighter auth limits remain. Returns 429 with Retry-After. Reads are not covered by this new budget. |
| Sensitive API responses could be cached | All normal API responses and error responses get Cache-Control: no-store, X-Content-Type-Options: nosniff, X-Frame-Options: DENY and Referrer-Policy: no-referrer. These API headers do not secure separately served frontend HTML. |
| Excessive/invalid input | Positive signed-32-bit record IDs in paths and request models; trimmed nonblank cohort names (100 characters) and plan titles (200); descriptions/comments capped at 10,000 characters. Bulk lists retain their 1,000-ID limits. Cohort creation rejects unknown fields. Existing longer stored text remains readable. Verify title/name limits against the actual database schema. |
| Validation reflected submitted data | All validation errors now omit input/context, retaining field location, message and error type. Unexpected errors return generic JSON, not internal details. Server-side exception logging still needs secure operational configuration. |
| DB connections leaked on failed queries | Ten legacy service functions now close connections/cursors on success or failure and use transaction contexts for commit/rollback. Their SQL and authorization behavior are retained. |
| Secret-file accidents | Added ignores for .env variants and private-key file extensions, allowing .env.example. This does not remove secrets already committed or protect Git history. |

The write budget shares the existing limiter store. Its default memory store is per process and resets on restart. Configure shared Redis before using multiple workers/instances. Clients on a shared office IP share the budget; tune using measured use. Trust forwarded client addresses only from the real reverse proxy, restrict direct access to the API port, and test client-IP handling on EC2. Do not set unrestricted forwarded-header trust on a publicly reachable Uvicorn port.

## Outstanding findings and release conditions

1. **Medium: browser-readable session token.** `frontend/src/auth/authStore.ts` persists the bearer token in localStorage. An XSS vulnerability could steal it. No exploitable XSS sink was found in this review, but this is a finding a security reviewer may flag. The existing login flow was preserved. Recommended follow-up: Secure, HttpOnly, SameSite cookies with explicit CSRF defenses and corresponding frontend/API tests. Moving the token to sessionStorage alone does not prevent XSS theft. See [OWASP local storage guidance](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html#local-storage).
2. **High if exposed without transport protections: deployment security is unverified.** Serve the site through HTTPS. Set frontend response headers at the reverse proxy, including a tested Content-Security-Policy and frame protection, plus HSTS once HTTPS is operational. API headers alone do not protect the SPA. CSP must account for Google Fonts and existing inline styles; avoid allowing arbitrary script execution. Restrict SSH, PostgreSQL and the API port appropriately. See [OWASP REST security guidance](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html).
3. **Medium: database TLS defaults permit fallback.** `backend/database.py` still defaults to `PG_SSLMODE=prefer` and the existing public EC2 hostname/IP. This preserves the current desktop connection, but is not a production TLS guarantee. Configure a suitable certificate/hostname and `PG_SSLMODE=verify-full` with `PGSSLROOTCERT` for a remote database; explicitly set PG_HOST, PG_DATABASE and PG_USER. Verify least-privilege grants on the real database. See [PostgreSQL certificate verification](https://www.postgresql.org/docs/current/libpq-ssl.html).
4. **Medium: abuse and account lifecycle remain limited.** IP limits are not distributed-attack protection. Public signup has no email verification/invitation requirement and discloses registered emails. Existing password minimum is eight characters with a special character; there is no breached-password screening or MFA. There is no account-disable, password-recovery or administrative session-revocation UI. Prioritize privileged-account protection and an enrollment policy before external use.
5. **Medium: resource controls require infrastructure support.** List/tracking endpoints have no pagination, and reads are not globally rate limited. There is no DB pool or statement timeout. Proxy request/body timeouts, concurrency limits and realistic load tests are still needed; a byte cap alone does not stop slow clients or distributed load.
6. **Medium: privileged-action audit history is absent.** Role, assignment and plan changes do not produce a durable actor/time/before/after audit trail. Existing notifications are not an audit log. This matters for investigating HR/Manager misuse and may be a review requirement.
7. **Low / business integrity: staff-assignment assumption is not enforced consistently.** Promotion checks for existing training, but assignment services can assign a trainee profile retained by a promoted HR/Manager. Concurrent promotion and assignment do not share the same user-row lock. This does not allow a trainee to promote themselves, but it can violate the assumption that staff have no training. Agree the invariant before tightening it across all assignment paths.
8. **Deployment reproducibility is incomplete.** Backend requirements are ranges/unpinned, public FastAPI docs remain enabled, and the repository currently contains no SQL migrations/baseline despite README references. Restore/version the actual schema and grants, pin/test the Linux dependency set, and decide whether to disable public docs. OpenAPI documentation does not bypass role checks. Required secrets are runtime environment variables; startup does not validate every required setting.

## Verification

- 333 backend tests passed, including existing authorization/ownership tests and 27 new security cases. New cases cover oversized and chunked bodies, invalid IDs/fields, shared write limits across paths, raw forwarded-header spoof attempts, error headers and connection cleanup on query failure.
- 18 Playwright browser tests passed; frontend production build passed.
- `npm audit --json`: zero reported vulnerabilities in the installed frontend dependency tree.
- `python -m pip_audit --format json`: no known vulnerabilities in the installed local Python environment. pip-audit was installed into the local .venv as an audit tool, not added to runtime requirements. This scan does not lock dependencies or attest to a future Linux install.
- A limited tracked-file scan found no AWS access-key IDs, private-key blocks or credential-bearing URLs. It is not a full secret scan or Git-history audit.
- Tests use mocked database connections and browser API responses. They do not establish live database permissions, transaction behavior under concurrency, TLS configuration or production capacity. Existing dependency deprecation warnings remain.

## EC2 handoff

The next phase should make updates repeatable: `git pull`, install pinned backend dependencies, apply reviewed migrations, `npm ci` and build, restart the managed backend service, then smoke-test through HTTPS. Put those repeatable steps in a deployment script once the EC2 OS, domain and actual database schema are confirmed. Initial setup also needs persistent secret injection, Nginx/reverse-proxy configuration, a process manager such as systemd, shared rate-limit storage if needed, backups and a tested rollback procedure. Git pull alone does none of these setup/restart steps.

All added middleware, validation constraints, response/error changes, resource-cleanup rewrites, tests and this report are AI-written changes for review. Existing SQL, role/ownership rules, authentication flow and React UI were reused. No deployment, commit or push was performed.

## Subsequent deployment preparation

The `deploy/` setup now supplies Nginx TLS termination, frontend CSP/security headers, loopback-only Uvicorn, production docs disabling and startup environment checks. `backend/requirements-production.txt` pins the tested Linux runtime set. A real Linux/Nginx/FastAPI HTTPS proxy test passed. These close the repository-configuration gaps described above, but must still be installed and verified on EC2; localStorage tokens, account lifecycle/audit-history decisions and the missing database schema/migrations remain outstanding.
