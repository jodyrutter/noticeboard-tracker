from psycopg2.extras import RealDictCursor
from database import get_connection
from services.workflow_notifications import notify_progress
from contextlib import closing


def get_progress_by_plan(plan_id):
    with closing(get_connection()) as connection, connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT id FROM plans WHERE id = %s;", (plan_id,))
            if cursor.fetchone() is None:
                return None
            cursor.execute("""
                SELECT * FROM progress_reports WHERE plan_id = %s
                ORDER BY submitted_at DESC;
            """, (plan_id,))
            return cursor.fetchall()



def create_progress_report(trainee_id, plan_id, status, comments, user_id):
    with closing(get_connection()) as connection, connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO progress_reports (trainee_id, plan_id, status, comments)
                SELECT t.id, %s, %s, %s FROM trainees t
                WHERE t.id = %s AND t.user_id = %s
                  AND EXISTS (
                      SELECT 1 FROM plan_assignments pa
                      WHERE pa.trainee_id = t.id AND pa.plan_id = %s
                  )
                RETURNING id;
            """, (plan_id, status, comments, trainee_id, user_id, plan_id))
            row = cursor.fetchone()
            if row:
                notify_progress(cursor, plan_id, user_id, status)
            return row[0] if row else None


def get_progress_by_trainee(trainee_id):
    with closing(get_connection()) as connection, connection:
        with closing(connection.cursor(cursor_factory=RealDictCursor)) as cursor:

            cursor.execute(
                """
                SELECT *
                FROM progress_reports
                WHERE trainee_id = %s
                ORDER BY submitted_at DESC;
                """,
                (trainee_id,)
            )

            rows = cursor.fetchall()


            return rows
