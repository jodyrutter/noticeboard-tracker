from database import get_connection

def get_all_cohorts():
    connection = get_connection()
    cursor = connection.cursor()
    
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