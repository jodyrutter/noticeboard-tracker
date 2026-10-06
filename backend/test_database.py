from database import get_connection
from lambda_function import lambda_handler

connection = get_connection()
cursor = connection.cursor()

event = {
    "requestContext": {
        "http": {
            "method": "POST"
        }
    },
    "rawPath": "/notifications",
    "body": """
    {
        "user_id": 3,
        "message": "New training plan assigned: AWS Deployment Week"
    }
    """
}

print(lambda_handler(event, None))

user_id = cursor.fetchone()[0]
connection.commit()

print("Created user with ID:", user_id)

cursor.close()
connection.close()