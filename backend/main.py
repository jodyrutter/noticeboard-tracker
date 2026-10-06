from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from auth_routes import router as auth_router, limiter, rate_limit_exceeded_handler

from schemas import TraineeCreate, CohortCreate, PlanCreate, ProgressCreate, NotificationCreate

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
from services.progress_service import (
    create_progress_report,
    get_progress_by_trainee
)
from services.notification_service import (
    create_notification,
    get_notifications_by_user,
    mark_notification_as_read
)
from services.dashboard_service import (
    get_dashboard_summary,
    get_trainee_overview
)

app = FastAPI(title="Noticeboard Tracker", version="0.1.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.include_router(auth_router)


# Avoid echoing passwords in validation errors.
@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    if request.url.path in ("/api/signup", "/api/login"):
        return JSONResponse(status_code=422, content={"detail": [
            {"loc": error["loc"], "msg": error["msg"], "type": error["type"]}
            for error in exc.errors()
        ]})
    return await request_validation_exception_handler(request, exc)

@app.get("/trainees")
def list_trainees():
    trainees = get_all_trainees()
    return trainees

@app.get("/cohorts")
def list_cohorts():
    cohorts = get_all_cohorts()
    return cohorts

@app.get("/plans")
def list_plans():
    plans = get_all_plans()
    return plans

@app.get("/progress/trainee/{trainee_id}")
def trainee_progress(trainee_id: int):
    progress = get_progress_by_trainee(trainee_id)
    return progress

@app.get("/notifications/{user_id}")
def user_notifications(user_id: int):
    notifications = get_notifications_by_user(user_id)
    return notifications

@app.get("/dashboard")
def dashboard():
    dashboard = get_dashboard_summary()
    return dashboard

@app.get("/dashboard/trainees")
def trainee_overview():
    trainees = get_trainee_overview()
    return trainees

@app.post("/trainees", status_code=201)
def add_trainee(body: TraineeCreate):
    trainee_id = create_trainee(
        body.user_id, body.cohort_id, body.status, body.onboarding_date
    )
    return {'id': trainee_id, 'message': 'Trainee created'}

@app.post("/cohorts", status_code=201)
def add_cohort(body: CohortCreate):
    cohort_id = create_cohort(body.name, body.start_date, body.end_date)
    return {'id': cohort_id, 'message': 'Cohort created'}

@app.post("/plans", status_code=201)
def add_plan(body: PlanCreate):
    plan_id = create_plan(body.title, body.description, body.due_date, body.created_by)
    return {'id': plan_id, 'message': 'Plan created'}

@app.post("/plans/{plan_id}/assign/trainee/{trainee_id}", status_code=201)
def assign_trainee(plan_id: int, trainee_id: int):
    assignment_id = assign_plan_to_trainee(plan_id, trainee_id)
    return {'id': assignment_id, 'message': 'Plan assigned to trainee'}

@app.post("/plans/{plan_id}/assign/cohort/{cohort_id}", status_code=201)
def assign_cohort(plan_id: int, cohort_id: int):
    assignment_ids = assign_plan_to_cohort(plan_id, cohort_id)
    return {'assignment_ids': assignment_ids, 'message': 'Plan assigned to cohort'}

@app.post("/progress", status_code=201)
def add_progress(body: ProgressCreate):
    progress_id = create_progress_report(body.trainee_id, body.plan_id, body.status, body.comments)
    return {'id': progress_id, 'message': 'Progress report created'}

@app.post("/notifications", status_code=201)
def add_notification(body: NotificationCreate):
    notification_id = create_notification(body.user_id, body.message)
    return {'id': notification_id, 'message': 'Notification created'}

@app.put("/notifications/{notification_id}/read")
def read_notification(notification_id: int):
    mark_notification_as_read(notification_id)
    return {'message': 'Notification marked as read'}
