from contextlib import closing
from psycopg2.errors import ForeignKeyViolation
from database import get_connection


class AlreadyAssignedError(Exception):
    pass


class AssignmentReferenceError(Exception):
    pass


def assign_plan_to_trainee(plan_id, trainee_id):
    try:
        with closing(get_connection()) as connection, connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO plan_assignments (plan_id, trainee_id)
                    VALUES (%s, %s)
                    ON CONFLICT (plan_id, trainee_id) DO NOTHING
                    RETURNING id;
                """, (plan_id, trainee_id))
                row = cursor.fetchone()
                if row is None:
                    raise AlreadyAssignedError
                return row[0]
    except ForeignKeyViolation as exc:
        raise AssignmentReferenceError from exc


def assign_plan_to_cohort(plan_id, cohort_id):
    try:
        with closing(get_connection()) as connection, connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM plans WHERE id = %s;", (plan_id,))
                if cursor.fetchone() is None:
                    raise AssignmentReferenceError
                cursor.execute("SELECT id FROM cohorts WHERE id = %s;", (cohort_id,))
                if cursor.fetchone() is None:
                    raise AssignmentReferenceError
                cursor.execute("SELECT id FROM trainees WHERE cohort_id = %s ORDER BY id;", (cohort_id,))
                trainees = cursor.fetchall()
                assignment_ids = []
                for trainee in trainees:
                    cursor.execute("""
                        INSERT INTO plan_assignments (plan_id, trainee_id)
                        VALUES (%s, %s)
                        ON CONFLICT (plan_id, trainee_id) DO NOTHING
                        RETURNING id;
                    """, (plan_id, trainee[0]))
                    row = cursor.fetchone()
                    if row:
                        assignment_ids.append(row[0])
                return assignment_ids
    except ForeignKeyViolation as exc:
        raise AssignmentReferenceError from exc
