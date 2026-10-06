from lambda_function import lambda_handler

event = {
    "requestContext": {
        "http": {
            "method": "GET"
        }
    },
    "rawPath": "/trainees"
}

response = lambda_handler(event, None)

print(response)