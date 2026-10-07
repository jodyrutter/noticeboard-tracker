from database import get_connection
from contextlib import closing
from psycopg2.extras import RealDictCursor


def get_cohort(cohort_id):
    with closing(get_connection()) as connection, connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM cohorts WHERE id = %s;", (cohort_id,))
            return cursor.fetchone()

def get_all_cohorts():
    with closing(get_connection()) as connection, connection:
        with closing(connection.cursor(cursor_factory=RealDictCursor)) as cursor:

            cursor.execute("SELECT * FROM cohorts;");
            rows = cursor.fetchall();


            return rows

    
def create_cohort(name, start_date, end_date):
    with closing(get_connection()) as connection, connection:
        with closing(connection.cursor()) as cursor:

            cursor.execute("INSERT INTO cohorts (name, start_date, end_date) VALUES (%s, %s, %s) RETURNING id;",
            (name, start_date, end_date));
            cohort_id = cursor.fetchone()[0];


            return cohort_id


class MissingCohortMemberError(Exception):
    pass


def update_cohort_members(cohort_id, add, remove):
    with closing(get_connection()) as connection, connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM cohorts WHERE id = %s;", (cohort_id,))
            if cursor.fetchone() is None:
                return None
            ids = sorted(set(add + remove))
            cursor.execute("SELECT id FROM trainees WHERE id = ANY(%s) ORDER BY id FOR UPDATE;", (ids,))
            if {r[0] for r in cursor.fetchall()} != set(ids):
                raise MissingCohortMemberError
            cursor.execute("""
                UPDATE trainees SET cohort_id = CASE WHEN id = ANY(%s) THEN %s ELSE NULL END
                WHERE id = ANY(%s) OR (cohort_id = %s AND id = ANY(%s))
                RETURNING id;
            """, (add, cohort_id, add, cohort_id, remove))
            return [r[0] for r in cursor.fetchall()]
