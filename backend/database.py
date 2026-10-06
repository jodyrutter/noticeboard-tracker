import os
import psycopg2


def get_connection():
    return psycopg2.connect(
        host="13.219.9.139",
        database="noticeboard",
        user="noticeboard_app",
        password=os.environ["PG_PASSWORD"],
        port=5432
    )