from database import get_connection
from contextlib import closing


def get_assigned_plans(user_id):
    with closing(get_connection()) as connection, connection:
        with connection.cursor() as cursor:
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
    cursor = connection.cursor()
    
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
