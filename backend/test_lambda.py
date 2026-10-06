from lambda_function import lambda_handler


event = {
    "requestContext": {
        "http": {
            "method": "GET"
        }
    },
    "rawPath": "/dashboard/trainees"
}


response = lambda_handler(event, None)

print(response)