import json

from services.trainee_service import (
    get_all_trainees,
    create_trainee
)

from services.cohort_service import (
    get_all_cohorts,
    create_cohort
)

from services.plan_service import (
    get_all_plans,
    create_plan
)

from services.assignment_service import (
    assign_plan_to_trainee,
    assign_plan_to_cohort
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
        
    if method == "GET" and path == "/plans":
        plans = get_all_plans()
        return response(200, plans)

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
        
    if method == "POST" and path == "/plans":
        body = json.loads(event.get("body") or "{}")

        plan_id = create_plan(
            body["title"],
            body["description"],
            body["due_date"],
            body["created_by"]
        )

        return response(
            201,
            {
                "id": plan_id,
                "message": "Plan created"
            }
        )
        
    if method == "POST" and path.startswith("/plans/") and "/assign/trainee/" in path:
        parts = path.strip("/").split("/")

        plan_id = int(parts[1])
        trainee_id = int(parts[4])

        assignment_id = assign_plan_to_trainee(
            plan_id,
            trainee_id
        )

        return response(
            201,
            {
                "id": assignment_id,
                "message": "Plan assigned to trainee"
            }
        )
        
    if method == "POST" and path.startswith("/plans/") and "/assign/cohort/" in path:
        parts = path.strip("/").split("/")

        plan_id = int(parts[1])
        cohort_id = int(parts[4])

        assignment_ids = assign_plan_to_cohort(
            plan_id,
            cohort_id
        )

        return response(
            201,
            {
                "assignment_ids": assignment_ids,
                "message": "Plan assigned to cohort"
            }
        )

    return response(404, {"error": "Route not found"})