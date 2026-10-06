from lambda_function import lambda_handler


event = {
    "requestContext": {
        "http": {
            "method": "PUT"
        }
    },
    "rawPath": "/notifications/1/read"
}


response = lambda_handler(event, None)

print(response)