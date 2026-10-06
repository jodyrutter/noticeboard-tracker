from lambda_function import lambda_handler

event = {
    "requestContext": {
        "http": {
            "method": "POST"
        }
    },
    "rawPath": "/trainees",
    "body": """
    {
        "user_id": 1,
        "cohort_id": 1,
        "status": "ACTIVE",
        "onboarding_date": "2026-10-06"
    }
    """
}

response = lambda_handler(event, None)

print(response)