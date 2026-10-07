from psycopg2.extras import RealDictCursor
from database import get_connection
from contextlib import closing


def create_notification(user_id, message):
    with closing(get_connection()) as connection, connection:
        with closing(connection.cursor()) as cursor:

            cursor.execute(
                """
                INSERT INTO notifications (user_id, message)
                VALUES (%s, %s)
                RETURNING id;
                """,
                (user_id, message)
            )

            notification_id = cursor.fetchone()[0]


            return notification_id


def get_notifications_by_user(user_id):
    with closing(get_connection()) as connection, connection:
        with closing(connection.cursor(cursor_factory=RealDictCursor)) as cursor:

            cursor.execute(
                """
                SELECT *
                FROM notifications
                WHERE user_id = %s
                ORDER BY created_at DESC;
                """,
                (user_id,)
            )

            rows = cursor.fetchall()


            return rows



def mark_notification_as_read(notification_id, user_id):
    with closing(get_connection()) as connection, connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE notifications SET is_read = TRUE
                WHERE id = %s AND user_id = %s RETURNING id;
            """, (notification_id, user_id))
            return cursor.fetchone() is not None


def get_unread_count(user_id):
    with closing(get_connection()) as connection, connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM notifications WHERE user_id = %s AND is_read = FALSE;", (user_id,))
            return cursor.fetchone()[0]
