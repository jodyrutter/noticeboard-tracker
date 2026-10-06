from lambda_function import lambda_handler

event = {
    "requestContext": {
        "http": {
            "method": "POST"
        }
    },
    "rawPath": "/cohorts",
    "body": """
    {
        "name": "October Full Stack Cohort",
        "start_date": "2026-10-06",
        "end_date": "2026-12-15"
    }
    """
}

response = lambda_handler(event, None)

print(response)