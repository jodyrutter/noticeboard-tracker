from database import get_connection
from contextlib import closing


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
            return row[0] if row else None


def get_progress_by_trainee(trainee_id):
    connection = get_connection()
    cursor = connection.cursor()

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

    cursor.close()
    connection.close()

    return rows
