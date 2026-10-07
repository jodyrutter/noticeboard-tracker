from contextlib import closing
from datetime import datetime, timedelta
from secrets import token_urlsafe

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from database import get_connection
from auth_models import SignupRequest, User


class EmailAlreadyExistsError(Exception):
    pass


password_hasher = PasswordHash.recommended()
# Verify a dummy hash when the email is not registered.
_dummy_hash = password_hasher.hash(token_urlsafe(32))


def _user(row) -> User:
    return User(user_id=row[0], name=row[1], email=row[2], role=row[3])


def create_user(user_data: SignupRequest) -> User:
    password_hash = password_hasher.hash(user_data.password)
    with closing(get_connection()) as connection, connection:
        with connection.cursor() as cursor:
            # The role is a SQL literal, never taken from a request.
            cursor.execute("""
                INSERT INTO users (name, email, password_hash, role)
                VALUES (%s, %s, %s, 'TRAINEE')
                ON CONFLICT (lower(btrim(email))) DO NOTHING
                RETURNING id, name, email, role;
            """, (user_data.name, user_data.email.strip().lower(), password_hash))
            row = cursor.fetchone()
            if row is None:
                raise EmailAlreadyExistsError
            return _user(row)


def authenticate(email: str, password: str) -> User | None:
    with closing(get_connection()) as connection, connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, email, role, password_hash FROM users
                WHERE lower(btrim(email)) = %s;
            """, (email.strip().lower(),))
            row = cursor.fetchone()
    try:
        valid = password_hasher.verify(password, row[4] if row and row[4] else _dummy_hash)
    except (UnknownHashError, ValueError):
        # Old manual test records have placeholder hashes, not usable passwords.
        password_hasher.verify(password, _dummy_hash)
        return None
    return _user(row) if row and valid else None


def create_session(session_id: str, user_id: int, now: datetime, expires_at: datetime) -> None:
    with closing(get_connection()) as connection, connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM auth_sessions WHERE expires_at <= %s;", (now,))
            cursor.execute("""
                INSERT INTO auth_sessions (session_id, user_id, last_activity, expires_at)
                VALUES (%s, %s, %s, %s);
            """, (session_id, user_id, now, expires_at))


def session_user(session_id: str, user_id: int, now: datetime, idle_timeout: timedelta) -> User | None:
    with closing(get_connection()) as connection, connection:
        with connection.cursor() as cursor:
            # Atomic check/touch avoids bringing a revoked session back to life.
            cursor.execute("""
                UPDATE auth_sessions AS s SET last_activity = %s
                FROM users AS u
                WHERE s.session_id = %s AND s.user_id = %s AND u.id = s.user_id
                  AND s.expires_at > %s AND s.last_activity > %s
                RETURNING u.id, u.name, u.email, u.role;
            """, (now, session_id, user_id, now, now - idle_timeout))
            row = cursor.fetchone()
            return _user(row) if row else None


def revoke_session(session_id: str, user_id: int) -> None:
    with closing(get_connection()) as connection, connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM auth_sessions WHERE session_id = %s AND user_id = %s;", (session_id, user_id))
