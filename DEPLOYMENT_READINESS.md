# NoticeBoardTracker: business readiness and AWS handoff

## Business workflow coverage

| Requirement | Current implementation | Remaining validation or decision |
| --- | --- | --- |
| HR onboarding | Public trainee signup, HR email picker, one-at-a-time enrollment, statuses, cohort membership management | Confirm existing duplicate profiles are resolved; decide whether open signup is appropriate for the organization. |
| Cohort and solo planning | Manager creates/edits plans; assignment editor adds/removes individual trainees or current cohort members | Cohort assignment is a snapshot of current members. New cohort members do not inherit old plans automatically. |
| Automated updates | In-app notifications for enrollment, new assignment, unassignment, and real plan edits | Apply migration 006 and verify with the actual PostgreSQL schema. This is in-app delivery, not email/SMS. |
| Progress feedback | Trainee submits progress only for their own assigned plan; its current Manager creator receives a notification | Define a reporting cadence and whether reminders should be scheduled. |
| Manager oversight | Existing activity dashboard plus latest-status tracking, overdue assignments, missing reports and active trainees without plans | Verify timezone/date expectations and performance using realistic record counts. |
| Avoid duplicate entries | Signup/email checks, trainee enrollment guard, unique plan/trainee assignments; repeated assignment writes do not duplicate notifications | Verify the deployed database's email and trainee uniqueness constraints and clean up legacy duplicates deliberately. |

The two new API operations are:

- `GET /dashboard/tracking`: MANAGER only. Returns latest state per currently assigned trainee/plan, summary counts, and active TRAINEE users whose profiles have no plans. An absent report counts as NOT_STARTED and missing; completed work is not overdue. The latest report uses submitted_at then ID to break ties. Current-state totals differ deliberately from historical report counts.
- `GET /notifications/{user_id}/unread-count`: authenticated owner only; another user's ID returns 403. The bell polls at most once per minute while visible and refreshes after marking a notification read.

Existing HR-only onboarding and Manager-only assignment/edit routes create notifications internally. Public `POST /notifications` remains disabled; clients cannot choose arbitrary recipients or impersonate system messages. Notification inserts use the same cursor and transaction as each business change, so notification failure rolls back the change. No-op edits and duplicate assignment saves do not notify. Progress notifications go to `plans.created_by` only if that account is still a Manager; there is no assigned-supervisor model yet. Removal keeps report history; reassigning the same plan reuses that history in latest-status tracking.

## Before deploying

1. **Apply and verify DB migrations as an administrator.** Apply 004/005 if outstanding and `backend/migrations/006_workflow_notifications.sql` before using the new flows. 006 grants notification insert/sequence access and adds query indexes. It changes no existing records. The repository does not currently include a complete baseline schema or the earlier auth migrations referenced in README; export/version the actual schema and grants before treating fresh-environment provisioning as reproducible. Do not guess or drop existing tables to compensate.
2. **Run a real PostgreSQL acceptance test.** Unit tests use connection doubles and browser tests mock HTTP. They do not verify your EC2 schema, grants, network access, or transactions on a live server. Use dedicated test accounts and plans, not production trainees.
3. **Configure persistent backend secrets and connection settings.** Set PG_PASSWORD and a stable random NOTICEBOARD_JWT_SECRET (at least 32 bytes) through the deployment runtime. No secrets belong in frontend VITE variables. Prefer AWS Secrets Manager with narrowly scoped runtime IAM permissions; secret retrieval/injection is an infrastructure step, not implemented by this app. See [AWS Secrets Manager guidance](https://docs.aws.amazon.com/secretsmanager/latest/userguide/best-practices.html).
4. **Configure database connectivity for the destination.** The code now accepts PG_HOST, PG_PORT, PG_DATABASE, PG_USER and PG_SSLMODE, with a 10-second connection timeout. Defaults preserve the current desktop setup, including the EC2 address; explicitly override them in production. Set PG_SSLMODE=verify-full and libpq's PGSSLROOTCERT to the trusted CA file after configuring the database certificate and matching hostname. Configure TLS on your self-managed EC2 PostgreSQL server; RDS-only settings do not apply to EC2. Restrict the database security group to approved application connections, not the whole internet. See [PostgreSQL TLS verification](https://www.postgresql.org/docs/current/libpq-ssl.html) and [EC2 security-group rules](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/security-group-rules-reference.html).
5. **Serve the frontend and backend over HTTPS.** Build frontend/dist. Configure SPA fallback for /app/* and reverse-proxy /backend/* to FastAPI with that prefix removed. Vite's development proxy is not your production proxy. Do not run uvicorn --reload in production. For Lambda, package Linux-compatible dependencies and keep the existing Mangum adapter; confirm API Gateway path mapping. Nothing has been deployed by this change.
6. **Verify rate limiting behind the actual proxy.** Auth rate limits exist. Set NOTICEBOARD_RATE_LIMIT_STORAGE_URI to shared Redis for multiple workers/instances. Configure trusted forwarded headers so a client cannot spoof its address and all users are not accidentally treated as one IP. Auth limits do not currently rate-limit business writes; add appropriate gateway/application write limits before exposing the system broadly.
7. **Prepare operations and recovery.** Configure application/error logging without passwords or bearer tokens, alert on 5xx and DB connectivity failures, take backups and test restore. Confirm safe rollback and migration procedures. Pin and scan backend dependencies before production; requirements currently use ranges and some unpinned packages. Frontend has a lockfile.
8. **Review account lifecycle.** Choose password recovery and email verification/invitation policies before external enrollment. Self-role changes are blocked, but there is no dedicated administrative account-deactivation or audit-history flow. Decide whether Managers should see all cohorts or only their assigned teams; current access is organization-wide, matching the existing MVP.
9. **Size the MVP.** List/tracking APIs currently return all matching records. Benchmark expected cohort sizes; pagination, indexes beyond those supplied, pooling and aggregation may be needed at larger scale. Avoid claiming production load capacity from mocked tests.

If moving PostgreSQL to RDS, use the [RDS TLS instructions](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL.Concepts.General.SSL.html) and [RDS security-group guidance](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Overview.RDSSecurityGroups.html). This is optional; your current database is on EC2.

## Local acceptance walkthrough after migration 006

1. Sign up a dedicated trainee. As HR, enroll them and assign their cohort. As that trainee, open the bell: onboarding should be present.
2. As Manager, create a dated plan and assign it to the trainee or cohort. The trainee sees the plan and an assignment notification. Save unchanged assignments again: no duplicate notification should appear.
3. Edit the title/description/due date. Assigned trainees receive an update notice. Saving identical values should not create another notice.
4. As the trainee, submit IN_PROGRESS, then BLOCKED, then COMPLETED. The Manager who created the plan receives these updates. Tracking shows only the latest status for this assignment, while historical report activity counts all submissions.
5. Use a past due date with noncompleted status to check Overdue. Use a fresh assignment with no report to check Missing reports. Enroll an active trainee with no plan to check the unassigned table.
6. Remove the assignment. The trainee gets an unassignment notice, loses access to that plan through assigned-plan routes, and reports remain stored. Check that the dashboard's current assignments no longer include it.
7. Mark a notification read; unread count drops. Try another user's notification ID and another role's management API: expect 403/404 as appropriate.

## Follow-up features requiring policy choices

- Scheduled reminders for overdue or stale progress: define cadence, time zone, recipients and quiet hours; use an authenticated internal scheduled worker with deduplication, not a public reminder-spam endpoint.
- Email/SMS delivery if users must be notified while signed out: add a durable outbox, provider, retries and delivery tracking. Current notifications are in-app and the badge polls while the app is visible.
- Persistent cohort-to-plan links if future members should inherit a plan. Current snapshot assignments were retained deliberately.
- Manager ownership boundaries, audit records for role/assignment changes, invitation flow and reporting exports as the organization needs them.

All new workflow notification helpers, transaction wiring, tracking service/UI,
unread-count API/bell, migration 006, configuration overrides and tests are
AI-written. Existing schemas/tables, auth dependencies, API client and shared
React components are reused. The changes have not modified your AWS resources
or applied any database migrations.
