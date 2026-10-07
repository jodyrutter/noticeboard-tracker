from contextlib import closing

from psycopg2.extras import RealDictCursor
from database import get_connection


class AssignedTrainingError(Exception):
    pass


def get_promotion_users():
    with closing(get_connection()) as connection, connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT u.id AS user_id, u.name, u.email, u.role
                FROM users u
                WHERE u.role IN ('HR', 'MANAGER') OR (
                    u.role = 'TRAINEE' AND NOT EXISTS (
                        SELECT 1 FROM trainees t
                        JOIN plan_assignments pa ON pa.trainee_id = t.id
                        WHERE t.user_id = u.id
                    )
                ) ORDER BY lower(u.email), u.id;
            """)
            rows = cursor.fetchall()
            return {
                "staff": [u for u in rows if u["role"] in ("HR", "MANAGER")],
                "eligible": [u for u in rows if u["role"] == "TRAINEE"],
            }


def update_user_role(user_id, role):
    with closing(get_connection()) as connection, connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT id FROM users WHERE id = %s FOR UPDATE;", (user_id,))
            if cursor.fetchone() is None:
                return None
            cursor.execute("""
                UPDATE users u SET role = %s
                WHERE u.id = %s AND NOT EXISTS (
                    SELECT 1 FROM trainees t
                    JOIN plan_assignments pa ON pa.trainee_id = t.id
                    WHERE t.user_id = u.id
                ) RETURNING u.id AS user_id, u.name, u.email, u.role;
            """, (role, user_id))
            user = cursor.fetchone()
            if user is None:
                raise AssignedTrainingError
            return user
