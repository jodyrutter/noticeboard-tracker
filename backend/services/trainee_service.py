from database import get_connection

def get_all_trainees():
    connection = get_connection()
    cursor = connection.cursor()
    
    cursor.execute("SELECT * FROM trainees;");
    rows = cursor.fetchall();
    
    cursor.close();
    connection.close();
    
    return rows
    
def create_trainee(id_user, id_cohort, trainee_status, user_onboarding_date):
    connection = get_connection()
    cursor = connection.cursor()
    
    cursor.execute("INSERT INTO trainees (user_id, cohort_id, status, onboarding_date) VALUES (%s, %s, %s, %s) RETURNING id;",
    (id_user, id_cohort, trainee_status, user_onboarding_date));
    trainee_id = cursor.fetchone()[0];
    connection.commit();
    
    cursor.close();
    connection.close();
    
    return trainee_id