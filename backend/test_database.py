from database import get_connection

connection = get_connection()
cursor = connection.cursor()

cursor.execute("SELECT * FROM users;")

rows = cursor.fetchall()

for row in rows:
    print(row)

cursor.close()
connection.close()