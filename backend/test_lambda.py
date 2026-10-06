from lambda_function import lambda_handler

event = {
    "requestContext": {
        "http": {
            "method": "POST"
        }
    },
    "rawPath": "/plans",
    "body": """
    {
        "title": "AWS Deployment Week",
        "description": "Deploy NoticeBoardTracker using AWS.",
        "due_date": "2026-10-15",
        "created_by": 2
    }
    """
}

response = lambda_handler(event, None)

print(response)