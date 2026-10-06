from lambda_function import lambda_handler

event = {
    "requestContext": {
        "http": {
            "method": "POST"
        }
    },
    "rawPath": "/progress",
    "body": """
    {
        "trainee_id": 6,
        "plan_id": 1,
        "status": "IN_PROGRESS",
        "comments": "Finished backend setup and working on deployment."
    }
    """
}

response = lambda_handler(event, None)

print(response)