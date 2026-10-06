from lambda_function import lambda_handler


if __name__ == "__main__":
    event = {
        "version": "2.0",
        "routeKey": "GET /dashboard/trainees",
        "rawPath": "/dashboard/trainees",
        "rawQueryString": "",
        "headers": {"host": "localhost"},
        "requestContext": {"http": {"method": "GET", "path": "/dashboard/trainees", "sourceIp": "127.0.0.1"}},
        "body": None,
        "isBase64Encoded": False,
    }

    response = lambda_handler(event, None)

    print(response)
