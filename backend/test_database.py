from database import get_connection

connection = get_connection()
cursor = connection.cursor()

cursor.execute("SELECT * FROM users;")
rows = cursor.fetchall()

print("Connected successfully.")
print("Users:", rows)

cursor.close()
connection.close()