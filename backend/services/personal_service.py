from contextlib import closing

from psycopg2.extras import RealDictCursor

from database import get_connection


class MultipleTraineeRecordsError(Exception):
    pass


def get_own_trainee(user_id, trainee_id=None):
    with closing(get_connection()) as connection, connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, user_id, cohort_id, status, onboarding_date
                FROM trainees WHERE user_id = %s AND (%s IS NULL OR id = %s)
                ORDER BY id;
            """, (user_id, trainee_id, trainee_id))
            rows = cursor.fetchall()
            if len(rows) > 1:
                raise MultipleTraineeRecordsError
            return rows[0] if rows else None


def get_own_cohort(user_id, cohort_id):
    with closing(get_connection()) as connection, connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT c.id, c.name, c.start_date, c.end_date FROM cohorts c
                WHERE c.id = %s AND EXISTS (
                    SELECT 1 FROM trainees t WHERE t.cohort_id = c.id AND t.user_id = %s
                );
            """, (cohort_id, user_id))
            return cursor.fetchone()


def get_own_progress(user_id, trainee_id=None, plan_id=None):
    with closing(get_connection()) as connection, connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT pr.* FROM progress_reports pr
                JOIN trainees t ON t.id = pr.trainee_id
                WHERE t.user_id = %s
                  AND (%s IS NULL OR t.id = %s)
                  AND (%s IS NULL OR pr.plan_id = %s)
                ORDER BY pr.submitted_at DESC;
            """, (user_id, trainee_id, trainee_id, plan_id, plan_id))
            return cursor.fetchall()
