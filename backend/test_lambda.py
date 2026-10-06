from lambda_function import lambda_handler

event = {
    "requestContext": {
        "http": {
            "method": "POST"
        }
    },
    "rawPath": "/plans/1/assign/cohort/1"
}

response = lambda_handler(event, None)

print(response)