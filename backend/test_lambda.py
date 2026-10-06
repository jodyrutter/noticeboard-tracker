from lambda_function import lambda_handler

event = {
    "requestContext": {
        "http": {
            "method": "GET"
        }
    },
    "rawPath": "/plans"
}\q

response = lambda_handler(event, None)

print(response)