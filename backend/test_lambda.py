from lambda_function import lambda_handler


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


response = lambda_handler(event, None)

print(response)