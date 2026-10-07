from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from auth_routes import router as auth_router, limiter, rate_limit_exceeded_handler

from auth import CurrentUser, HRUser, ManagerUser, TraineeUser, StaffUser

from services.personal_service import get_own_trainee, get_own_cohort, get_own_progress, MultipleTraineeRecordsError

from schemas import CohortMembersUpdate, RoleUpdate, TraineeReplace, TraineeUpdate, TraineeCreate, CohortCreate, PlanCreate, ProgressCreate, NotificationCreate

from services.trainee_service import (
    get_all_trainees, get_unenrolled_users, TraineeAlreadyExistsError,
    create_trainee, update_trainee, get_trainee, InvalidTraineeUserError, InvalidCohortError
)
from services.cohort_service import (
    get_all_cohorts,
    create_cohort, get_cohort, update_cohort_members, MissingCohortMemberError
)
from services.plan_service import (
    get_all_plans,
    create_plan, get_assigned_plans, get_plan, update_plan, delete_plan, PlanInUseError
)
from services.assignment_service import (
    assign_plan_to_trainee, AlreadyAssignedError, AssignmentReferenceError,
    assign_plan_to_cohort
)
from services.progress_service import (
    create_progress_report,
    get_progress_by_trainee, get_progress_by_plan
)
from services.notification_service import (
    get_notifications_by_user,
    mark_notification_as_read
)
from services.dashboard_service import (
    get_dashboard_summary,
    get_trainee_overview
)

from services.promotion_service import get_promotion_users, update_user_role, AssignedTrainingError

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

@app.get("/users/promotion")
def promotion_users(current_user: HRUser):
    return get_promotion_users()


@app.patch("/users/{user_id}/role")
def change_user_role(user_id: int, body: RoleUpdate, current_user: HRUser):
    user = update_user_role(user_id, body.role)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.exception_handler(AssignedTrainingError)
async def assigned_training(request: Request, exc: AssignedTrainingError):
    return JSONResponse(status_code=409, content={"detail": "This user has assigned training and cannot change roles."})


@app.get("/users/unenrolled")
def unenrolled_users(current_user: HRUser):
    return get_unenrolled_users()


@app.exception_handler(TraineeAlreadyExistsError)
async def trainee_already_exists(request: Request, exc: TraineeAlreadyExistsError):
    return JSONResponse(status_code=409, content={"detail": "This user is already enrolled as a trainee. Refresh the available users and choose another email."})


@app.get("/trainees")
def list_trainees(current_user: StaffUser):
    trainees = get_all_trainees()
    return trainees

@app.get("/cohorts")
def list_cohorts(current_user: StaffUser):
    cohorts = get_all_cohorts()
    return cohorts

@app.get("/plans")
def list_plans(current_user: CurrentUser):
    plans = get_all_plans() if current_user.role == "MANAGER" else get_assigned_plans(current_user.user_id)
    return plans

@app.get("/progress/trainee/{trainee_id}")
def trainee_progress(trainee_id: int, current_user: CurrentUser):
    if current_user.role != "MANAGER":
        if get_own_trainee(current_user.user_id, trainee_id) is None:
            raise HTTPException(status_code=404, detail="Trainee not found")
        return get_own_progress(current_user.user_id, trainee_id=trainee_id)
    progress = get_progress_by_trainee(trainee_id)
    return progress

@app.get("/notifications/{user_id}")
def user_notifications(user_id: int, current_user: CurrentUser):
    if user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="You can only view your own notifications")
    notifications = get_notifications_by_user(user_id)
    return notifications

@app.get("/dashboard")
def dashboard(current_user: ManagerUser):
    dashboard = get_dashboard_summary()
    return dashboard

@app.get("/dashboard/trainees")
def trainee_overview(current_user: ManagerUser):
    trainees = get_trainee_overview()
    return trainees

@app.post("/trainees", status_code=201)
def add_trainee(body: TraineeCreate, current_user: HRUser):
    trainee_id = create_trainee(
        body.user_id, body.cohort_id, body.status, body.onboarding_date
    )
    return {'id': trainee_id, 'message': 'Trainee created'}

@app.post("/cohorts", status_code=201)
def add_cohort(body: CohortCreate, current_user: HRUser):
    cohort_id = create_cohort(body.name, body.start_date, body.end_date)
    return {'id': cohort_id, 'message': 'Cohort created'}

@app.post("/plans", status_code=201)
def add_plan(body: PlanCreate, current_user: ManagerUser):
    plan_id = create_plan(body.title, body.description, body.due_date, current_user.user_id)
    return {'id': plan_id, 'message': 'Plan created'}

@app.patch("/cohorts/{cohort_id}/members")
def edit_cohort_members(cohort_id: int, body: CohortMembersUpdate, current_user: HRUser):
    updated = update_cohort_members(cohort_id, body.add, body.remove)
    if updated is None:
        raise HTTPException(status_code=404, detail="Cohort not found")
    return {"updated_ids": updated}


@app.exception_handler(MissingCohortMemberError)
async def missing_cohort_member(request: Request, exc: MissingCohortMemberError):
    return JSONResponse(status_code=409, content={"detail": "A selected trainee no longer exists. Reopen the cohort to refresh its members."})


@app.exception_handler(AlreadyAssignedError)
async def already_assigned(request: Request, exc: AlreadyAssignedError):
    return JSONResponse(status_code=409, content={"detail": "This plan is already assigned to this trainee."})


@app.exception_handler(AssignmentReferenceError)
async def invalid_assignment_reference(request: Request, exc: AssignmentReferenceError):
    return JSONResponse(status_code=404, content={"detail": "The plan or assignment target no longer exists. Refresh and try again."})


@app.post("/plans/{plan_id}/assign/trainee/{trainee_id}", status_code=201)
def assign_trainee(plan_id: int, trainee_id: int, current_user: ManagerUser):
    assignment_id = assign_plan_to_trainee(plan_id, trainee_id)
    return {'id': assignment_id, 'message': 'Plan assigned to trainee'}

@app.post("/plans/{plan_id}/assign/cohort/{cohort_id}", status_code=201)
def assign_cohort(plan_id: int, cohort_id: int, current_user: ManagerUser):
    assignment_ids = assign_plan_to_cohort(plan_id, cohort_id)
    return {'assignment_ids': assignment_ids, 'message': 'Plan assigned to cohort'}

@app.post("/progress", status_code=201)
def add_progress(body: ProgressCreate, current_user: TraineeUser):
    trainee = get_own_trainee(current_user.user_id, body.trainee_id)
    if trainee is None:
        raise HTTPException(status_code=403, detail="No matching trainee profile belongs to your account")
    progress_id = create_progress_report(trainee["id"], body.plan_id, body.status, body.comments, current_user.user_id)
    if progress_id is None:
        raise HTTPException(status_code=403, detail="You can only submit progress for your own assigned plans")
    return {'id': progress_id, 'message': 'Progress report created'}

@app.post("/notifications", status_code=201)
def add_notification(body: NotificationCreate, current_user: CurrentUser):
    raise HTTPException(status_code=403, detail="Notification creation is not enabled for any MVP role")

@app.put("/notifications/{notification_id}/read")
def read_notification(notification_id: int, current_user: CurrentUser):
    if not mark_notification_as_read(notification_id, current_user.user_id):
        raise HTTPException(status_code=404, detail="Notification not found")
    return {'message': 'Notification marked as read'}


@app.patch("/trainees/{trainee_id}")
def edit_trainee(trainee_id: int, body: TraineeUpdate, current_user: HRUser):
    updated_id = update_trainee(trainee_id, body.model_dump(exclude_unset=True))
    if updated_id is None:
        raise HTTPException(status_code=404, detail="Trainee not found")
    return {"id": updated_id, "message": "Trainee updated"}


@app.exception_handler(InvalidTraineeUserError)
async def invalid_trainee_user(request: Request, exc: InvalidTraineeUserError):
    return JSONResponse(status_code=400, content={"detail": "Select an existing user with the TRAINEE role"})


@app.exception_handler(InvalidCohortError)
async def invalid_cohort(request: Request, exc: InvalidCohortError):
    return JSONResponse(status_code=400, content={"detail": "Cohort does not exist"})


@app.get("/trainees/{trainee_id}")
def trainee_detail(trainee_id: int, current_user: CurrentUser):
    trainee = get_trainee(trainee_id) if current_user.role in ("HR", "MANAGER") else get_own_trainee(current_user.user_id, trainee_id)
    if trainee is None:
        raise HTTPException(status_code=404, detail="Trainee not found")
    return trainee


@app.put("/trainees/{trainee_id}")
def replace_trainee(trainee_id: int, body: TraineeReplace, current_user: HRUser):
    updated_id = update_trainee(trainee_id, body.model_dump())
    if updated_id is None:
        raise HTTPException(status_code=404, detail="Trainee not found")
    return {"id": updated_id, "message": "Trainee updated"}


@app.get("/cohorts/{cohort_id}")
def cohort_detail(cohort_id: int, current_user: CurrentUser):
    cohort = get_cohort(cohort_id) if current_user.role in ("HR", "MANAGER") else get_own_cohort(current_user.user_id, cohort_id)
    if cohort is None:
        raise HTTPException(status_code=404, detail="Cohort not found")
    return cohort


@app.get("/plans/{plan_id}")
def plan_detail(plan_id: int, current_user: CurrentUser):
    plan = get_plan(plan_id, None if current_user.role == "MANAGER" else current_user.user_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@app.put("/plans/{plan_id}")
def edit_plan(plan_id: int, body: PlanCreate, current_user: ManagerUser):
    updated_id = update_plan(plan_id, body.title, body.description, body.due_date)
    if updated_id is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"id": updated_id, "message": "Plan updated"}


@app.delete("/plans/{plan_id}", status_code=204)
def remove_plan(plan_id: int, current_user: ManagerUser):
    if not delete_plan(plan_id):
        raise HTTPException(status_code=404, detail="Plan not found")
    return Response(status_code=204)


@app.get("/progress/plan/{plan_id}")
def plan_progress(plan_id: int, current_user: CurrentUser):
    if current_user.role != "MANAGER":
        if get_plan(plan_id, current_user.user_id) is None:
            raise HTTPException(status_code=404, detail="Plan not found")
        return get_own_progress(current_user.user_id, plan_id=plan_id)
    progress = get_progress_by_plan(plan_id)
    if progress is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return progress


@app.exception_handler(PlanInUseError)
async def plan_in_use(request: Request, exc: PlanInUseError):
    return JSONResponse(status_code=409, content={"detail": "Cannot delete a plan with assignments or progress reports"})


@app.exception_handler(MultipleTraineeRecordsError)
async def ambiguous_trainee(request: Request, exc: MultipleTraineeRecordsError):
    return JSONResponse(status_code=409, content={"detail": "Multiple trainee profiles found; specify your trainee ID or ask HR to resolve them"})
