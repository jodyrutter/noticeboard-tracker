from database import get_connection
from contextlib import closing
from psycopg2.errors import ForeignKeyViolation
from psycopg2.extras import RealDictCursor


class PlanInUseError(Exception):
    pass


def get_plan(plan_id, user_id=None):
    with closing(get_connection()) as connection, connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            if user_id is None:
                cursor.execute("SELECT * FROM plans WHERE id = %s;", (plan_id,))
            else:
                cursor.execute("""
                    SELECT p.* FROM plans p WHERE p.id = %s AND EXISTS (
                        SELECT 1 FROM plan_assignments pa
                        JOIN trainees t ON t.id = pa.trainee_id
                        WHERE pa.plan_id = p.id AND t.user_id = %s
                    );
                """, (plan_id, user_id))
            return cursor.fetchone()


def update_plan(plan_id, title, description, due_date):
    with closing(get_connection()) as connection, connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE plans SET title = %s, description = %s, due_date = %s
                WHERE id = %s RETURNING id;
            """, (title, description, due_date, plan_id))
            row = cursor.fetchone()
            return row[0] if row else None


def delete_plan(plan_id):
    try:
        with closing(get_connection()) as connection, connection:
            with connection.cursor() as cursor:
                # Lock the parent before checking references to prevent concurrent assignments.
                cursor.execute("SELECT id FROM plans WHERE id = %s FOR UPDATE;", (plan_id,))
                if cursor.fetchone() is None:
                    return False
                cursor.execute("""
                    SELECT EXISTS (SELECT 1 FROM plan_assignments WHERE plan_id = %s)
                        OR EXISTS (SELECT 1 FROM progress_reports WHERE plan_id = %s);
                """, (plan_id, plan_id))
                if cursor.fetchone()[0]:
                    raise PlanInUseError
                cursor.execute("DELETE FROM plans WHERE id = %s;", (plan_id,))
                return True
    except ForeignKeyViolation as exc:
        raise PlanInUseError from exc


def get_assigned_plans(user_id):
    with closing(get_connection()) as connection, connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT p.* FROM plans p
                WHERE EXISTS (
                    SELECT 1 FROM plan_assignments pa
                    JOIN trainees t ON t.id = pa.trainee_id
                    WHERE pa.plan_id = p.id AND t.user_id = %s
                ) ORDER BY p.id;
            """, (user_id,))
            return cursor.fetchall()


def get_all_plans():
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("SELECT * FROM plans;");
    rows = cursor.fetchall();
    
    cursor.close();
    connection.close();
    
    return rows

    
def create_plan(plan_title, plan_description, plan_due_date, plan_created_by):
    connection = get_connection()
    cursor = connection.cursor()
    
    cursor.execute("INSERT INTO plans (title, description, due_date, created_by) VALUES (%s, %s, %s, %s) RETURNING id;",
    (plan_title, plan_description, plan_due_date, plan_created_by));
    plan_id = cursor.fetchone()[0];
    connection.commit();
    
    cursor.close();
    connection.close();
    
    return plan_id
