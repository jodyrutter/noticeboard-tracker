from database import get_connection
from contextlib import closing


def create_notification(user_id, message):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO notifications (user_id, message)
        VALUES (%s, %s)
        RETURNING id;
        """,
        (user_id, message)
    )

    notification_id = cursor.fetchone()[0]

    connection.commit()
    cursor.close()
    connection.close()

    return notification_id


def get_notifications_by_user(user_id):
    connection = get_connection()
    cursor = connection.cursor()

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

    cursor.close()
    connection.close()

    return rows


def mark_notification_as_read(notification_id, user_id):
    with closing(get_connection()) as connection, connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE notifications SET is_read = TRUE
                WHERE id = %s AND user_id = %s RETURNING id;
            """, (notification_id, user_id))
            return cursor.fetchone() is not None
