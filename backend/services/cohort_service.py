from database import get_connection
from contextlib import closing
from psycopg2.extras import RealDictCursor


def get_cohort(cohort_id):
    with closing(get_connection()) as connection, connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM cohorts WHERE id = %s;", (cohort_id,))
            return cursor.fetchone()

def get_all_cohorts():
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("SELECT * FROM cohorts;");
    rows = cursor.fetchall();
    
    cursor.close();
    connection.close();
    
    return rows

    
def create_cohort(name, start_date, end_date):
    connection = get_connection()
    cursor = connection.cursor()
    
    cursor.execute("INSERT INTO cohorts (name, start_date, end_date) VALUES (%s, %s, %s) RETURNING id;",
    (name, start_date, end_date));
    cohort_id = cursor.fetchone()[0];
    connection.commit();
    
    cursor.close();
    connection.close();
    
    return cohort_id
