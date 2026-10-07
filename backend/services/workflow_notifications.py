def notify_plan_trainees(cursor, plan_id, trainee_ids, action):
    if not trainee_ids:
        return
    cursor.execute("""
        INSERT INTO notifications (user_id, message)
        SELECT DISTINCT t.user_id, %s || p.title
        FROM trainees t CROSS JOIN plans p
        WHERE p.id = %s AND t.id = ANY(%s);
    """, (action + ": ", plan_id, trainee_ids))


def notify_plan_update(cursor, plan_id):
    cursor.execute("""
        INSERT INTO notifications (user_id, message)
        SELECT DISTINCT t.user_id, 'Training plan updated: ' || p.title
        FROM plan_assignments pa JOIN trainees t ON t.id = pa.trainee_id
        JOIN plans p ON p.id = pa.plan_id WHERE p.id = %s;
    """, (plan_id,))


def notify_progress(cursor, plan_id, user_id, status):
    cursor.execute("""
        INSERT INTO notifications (user_id, message)
        SELECT manager.id, learner.name || ' reported ' || %s || ' for ' || p.title
        FROM plans p JOIN users manager ON manager.id = p.created_by
        JOIN users learner ON learner.id = %s
        WHERE p.id = %s AND manager.role = 'MANAGER';
    """, (status, user_id, plan_id))
