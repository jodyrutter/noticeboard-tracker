from contextlib import closing
from psycopg2.extras import RealDictCursor
from database import get_connection


def get_tracking():
    with closing(get_connection()) as connection, connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT t.id AS trainee_id, u.name, u.email, c.name AS cohort,
                       p.id AS plan_id, p.title, p.due_date,
                       COALESCE(latest.status, 'NOT_STARTED') AS status,
                       latest.submitted_at AS last_report_at,
                       latest.id IS NULL AS missing_report,
                       COALESCE(p.due_date < CURRENT_DATE AND
                           COALESCE(latest.status, 'NOT_STARTED') <> 'COMPLETED', FALSE) AS overdue
                FROM plan_assignments pa
                JOIN trainees t ON t.id = pa.trainee_id
                JOIN users u ON u.id = t.user_id
                JOIN plans p ON p.id = pa.plan_id
                LEFT JOIN cohorts c ON c.id = t.cohort_id
                LEFT JOIN LATERAL (
                    SELECT pr.id, pr.status, pr.submitted_at FROM progress_reports pr
                    WHERE pr.trainee_id = t.id AND pr.plan_id = p.id
                    ORDER BY pr.submitted_at DESC, pr.id DESC LIMIT 1
                ) latest ON TRUE
                ORDER BY overdue DESC, u.name, p.id;
            """)
            assignments = cursor.fetchall()
            cursor.execute("""
                SELECT t.id AS trainee_id, u.name, u.email, c.name AS cohort
                FROM trainees t JOIN users u ON u.id = t.user_id
                LEFT JOIN cohorts c ON c.id = t.cohort_id
                WHERE t.status = 'ACTIVE' AND u.role = 'TRAINEE' AND NOT EXISTS (
                    SELECT 1 FROM plan_assignments pa WHERE pa.trainee_id = t.id
                ) ORDER BY u.name, t.id;
            """)
            unassigned = cursor.fetchall()
    summary = {status: sum(r["status"] == status for r in assignments)
               for status in ("NOT_STARTED", "IN_PROGRESS", "COMPLETED", "BLOCKED")}
    summary.update(total_assignments=len(assignments),
                   overdue=sum(r["overdue"] for r in assignments),
                   missing_reports=sum(r["missing_report"] for r in assignments),
                   unassigned_trainees=len(unassigned))
    return {"summary": summary, "assignments": assignments, "unassigned_trainees": unassigned}
