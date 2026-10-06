from database import get_connection

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