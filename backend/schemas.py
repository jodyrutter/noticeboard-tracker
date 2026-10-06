from datetime import date

from pydantic import BaseModel


class TraineeCreate(BaseModel):
    user_id: int
    cohort_id: int | None
    status: str
    onboarding_date: date


class CohortCreate(BaseModel):
    name: str
    start_date: date
    end_date: date | None


class PlanCreate(BaseModel):
    title: str
    description: str | None
    due_date: date | None
    created_by: int


class ProgressCreate(BaseModel):
    trainee_id: int
    plan_id: int
    status: str
    comments: str | None


class NotificationCreate(BaseModel):
    user_id: int
    message: str
