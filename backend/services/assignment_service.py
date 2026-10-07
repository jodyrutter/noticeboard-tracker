from contextlib import closing
from psycopg2.errors import ForeignKeyViolation
from database import get_connection
from services.workflow_notifications import notify_plan_trainees


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
                notify_plan_trainees(cursor, plan_id, [trainee_id], "Training plan assigned")
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
                        notify_plan_trainees(cursor, plan_id, [trainee[0]], "Training plan assigned")
                return assignment_ids
    except ForeignKeyViolation as exc:
        raise AssignmentReferenceError from exc


def get_plan_assignments(plan_id):
    with closing(get_connection()) as connection, connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM plans WHERE id = %s;", (plan_id,))
            if cursor.fetchone() is None:
                return None
            cursor.execute("SELECT trainee_id FROM plan_assignments WHERE plan_id = %s ORDER BY trainee_id;", (plan_id,))
            return [row[0] for row in cursor.fetchall()]


def update_plan_assignments(plan_id, add, remove):
    try:
        with closing(get_connection()) as connection, connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM plans WHERE id = %s FOR UPDATE;", (plan_id,))
                if cursor.fetchone() is None:
                    return None
                cursor.execute("SELECT id FROM trainees WHERE id = ANY(%s);", (add,))
                if {row[0] for row in cursor.fetchall()} != set(add):
                    raise AssignmentReferenceError
                cursor.execute("DELETE FROM plan_assignments WHERE plan_id = %s AND trainee_id = ANY(%s) RETURNING trainee_id;", (plan_id, remove))
                removed = [row[0] for row in cursor.fetchall()]
                notify_plan_trainees(cursor, plan_id, removed, "Training plan unassigned")
                for trainee_id in sorted(set(add)):
                    cursor.execute("""
                        INSERT INTO plan_assignments (plan_id, trainee_id) VALUES (%s, %s)
                        ON CONFLICT (plan_id, trainee_id) DO NOTHING RETURNING id;
                    """, (plan_id, trainee_id))
                    if cursor.fetchone() is not None:
                        notify_plan_trainees(cursor, plan_id, [trainee_id], "Training plan assigned")
                cursor.execute("SELECT trainee_id FROM plan_assignments WHERE plan_id = %s ORDER BY trainee_id;", (plan_id,))
                return [row[0] for row in cursor.fetchall()]
    except ForeignKeyViolation as exc:
        raise AssignmentReferenceError from exc
