import os
import psycopg2


def get_connection():
    return psycopg2.connect(
        host=os.environ.get("PG_HOST", "13.219.9.139"),
        database=os.environ.get("PG_DATABASE", "noticeboard"),
        user=os.environ.get("PG_USER", "noticeboard_app"),
        password=os.environ["PG_PASSWORD"],
        port=int(os.environ.get("PG_PORT", "5432")),
        sslmode=os.environ.get("PG_SSLMODE", "prefer"),
        connect_timeout=10
    )