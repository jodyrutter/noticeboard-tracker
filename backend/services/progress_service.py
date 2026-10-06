from database import get_connection


def create_progress_report(trainee_id, plan_id, status, comments):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO progress_reports
        (trainee_id, plan_id, status, comments)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
        """,
        (trainee_id, plan_id, status, comments)
    )

    progress_id = cursor.fetchone()[0]

    connection.commit()
    cursor.close()
    connection.close()

    return progress_id


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