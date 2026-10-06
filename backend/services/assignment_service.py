from database import get_connection


def assign_plan_to_trainee(plan_id, trainee_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO plan_assignments (plan_id, trainee_id)
        VALUES (%s, %s)
        RETURNING id;
        """,
        (plan_id, trainee_id)
    )

    assignment_id = cursor.fetchone()[0]

    connection.commit()
    cursor.close()
    connection.close()

    return assignment_id

def assign_plan_to_cohort(plan_id, cohort_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id
        FROM trainees
        WHERE cohort_id = %s;
        """,
        (cohort_id,)
    )

    trainees = cursor.fetchall()

    assignment_ids = []

    for trainee in trainees:
        trainee_id = trainee[0]

        cursor.execute(
            """
            INSERT INTO plan_assignments (plan_id, trainee_id)
            VALUES (%s, %s)
            ON CONFLICT (plan_id, trainee_id) DO NOTHING
            RETURNING id;
            """,
            (plan_id, trainee_id)
        )

        result = cursor.fetchone()

        if result:
            assignment_ids.append(result[0])

    connection.commit()
    cursor.close()
    connection.close()

    return assignment_ids