from database import get_connection


if __name__ == "__main__":
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO users (name, email, password_hash, role)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
    """, (
        "Test Manager",
        "manager@test.com",
        "temporary",
        "MANAGER"
    ))

    user_id = cursor.fetchone()[0]

    connection.commit()

    print("Created user with ID:", user_id)

    cursor.close()

    connection.close()
