from database import get_connection
from contextlib import closing
from psycopg2 import sql
from psycopg2.errors import ForeignKeyViolation
from psycopg2.extras import RealDictCursor


class InvalidTraineeUserError(Exception):
    pass


class InvalidCohortError(Exception):
    pass


def get_trainee(trainee_id):
    with closing(get_connection()) as connection, connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM trainees WHERE id = %s;", (trainee_id,))
            return cursor.fetchone()

def get_all_trainees():
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("SELECT t.*, u.name, u.email, c.name AS cohort_name FROM trainees t JOIN users u ON u.id = t.user_id LEFT JOIN cohorts c ON c.id = t.cohort_id ORDER BY t.id;");
    rows = cursor.fetchall();
    
    cursor.close();
    connection.close();
    
    return rows

    
def create_trainee(id_user, id_cohort, trainee_status, user_onboarding_date):
    try:
        with closing(get_connection()) as connection, connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO trainees (user_id, cohort_id, status, onboarding_date)
                    SELECT id, %s, %s, %s FROM users
                    WHERE id = %s AND role = 'TRAINEE'
                    RETURNING id;
                """, (id_cohort, trainee_status, user_onboarding_date, id_user))
                row = cursor.fetchone()
                if row is None:
                    raise InvalidTraineeUserError
                return row[0]
    except ForeignKeyViolation as exc:
        raise InvalidCohortError from exc


def update_trainee(trainee_id, changes):
    allowed = {"cohort_id", "status", "onboarding_date"}
    if not changes or not set(changes).issubset(allowed):
        raise ValueError("Invalid trainee update fields")
    assignments = sql.SQL(", ").join(
        sql.SQL("{} = %s").format(sql.Identifier(field)) for field in changes
    )
    try:
        with closing(get_connection()) as connection, connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    sql.SQL("UPDATE trainees SET {} WHERE id = %s RETURNING id;").format(assignments),
                    (*changes.values(), trainee_id),
                )
                row = cursor.fetchone()
                return row[0] if row else None
    except ForeignKeyViolation as exc:
        raise InvalidCohortError from exc
