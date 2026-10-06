-- Run as a DB admin, not automatically on app startup.
-- Requires existing users(id, name, email, password_hash, role).
-- Check that role accepts TRAINEE, HR, MANAGER (enum/check schema not in repo).
-- This transaction fails rather than deleting/merging duplicate emails.
BEGIN;

ALTER TABLE users ALTER COLUMN role SET DEFAULT 'TRAINEE';
CREATE UNIQUE INDEX users_auth_email_unique ON users (lower(btrim(email)));

CREATE TABLE auth_sessions (
    session_id TEXT PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    last_activity TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX auth_sessions_expires_at_idx ON auth_sessions (expires_at);
CREATE INDEX auth_sessions_user_id_idx ON auth_sessions (user_id);
GRANT SELECT, INSERT, UPDATE, DELETE ON auth_sessions TO noticeboard_app;

COMMIT;
