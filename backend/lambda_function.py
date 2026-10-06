import json

from services.trainee_service import (
    get_all_trainees,
    create_trainee
)

from services.cohort_service import (
    get_all_cohorts,
    create_cohort
)


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(body, default=str)
    }


def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method")
    path = event.get("rawPath", "")

    if method == "GET" and path == "/trainees":
        trainees = get_all_trainees()
        return response(200, trainees)
        
    if method == "GET" and path == "/cohorts":
        cohorts = get_all_cohorts()
        return response(200, cohorts)

    if method == "POST" and path == "/trainees":
        body = json.loads(event.get("body") or "{}")

        trainee_id = create_trainee(
            body["user_id"],
            body["cohort_id"],
            body["status"],
            body["onboarding_date"]
        )

        return response(
            201,
            {
                "id": trainee_id,
                "message": "Trainee created"
            }
        )
        
    if method == "POST" and path == "/cohorts":
        body = json.loads(event.get("body") or "{}")

        cohort_id = create_cohort(
            body["name"],
            body["start_date"],
            body["end_date"]
        )

        return response(
            201,
            {
                "id": cohort_id,
                "message": "Cohort created"
            }
        )

    return response(404, {"error": "Route not found"})