from database import get_connection


def get_dashboard_summary():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM trainees;
    """)
    total_trainees = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM trainees
        WHERE status = 'ACTIVE';
    """)
    active_trainees = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM cohorts;
    """)
    total_cohorts = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM progress_reports
        WHERE status = 'COMPLETED';
    """)
    completed_reports = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM progress_reports
        WHERE status = 'IN_PROGRESS';
    """)
    in_progress_reports = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM progress_reports
        WHERE status = 'BLOCKED';
    """)
    blocked_reports = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM plan_assignments pa
        WHERE NOT EXISTS (
            SELECT 1
            FROM progress_reports pr
            WHERE pr.plan_id = pa.plan_id
              AND pr.trainee_id = pa.trainee_id
        );
    """)
    missing_reports = cursor.fetchone()[0]

    cursor.close()
    connection.close()

    return {
        "total_trainees": total_trainees,
        "active_trainees": active_trainees,
        "total_cohorts": total_cohorts,
        "completed_reports": completed_reports,
        "in_progress_reports": in_progress_reports,
        "blocked_reports": blocked_reports,
        "missing_reports": missing_reports
    }
    
def get_trainee_overview():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("
        SELECT
            t.id AS trainee_id,
            u.name,
            u.email,
            c.name AS cohort_name,
            t.status AS trainee_status
        FROM trainees t
        JOIN users u
            ON t.user_id = u.id
        LEFT JOIN cohorts c
            ON t.cohort_id = c.id
        ORDER BY u.name;")

    rows = cursor.fetchall()

    trainees = []

    for row in rows:
        trainees.append({
            "trainee_id": row[0],
            "name": row[1],
            "email": row[2],
            "cohort": row[3],
            "status": row[4]
        })

    cursor.close()
    connection.close()

    return trainees