from datetime import date

from pydantic import BaseModel, ConfigDict, model_validator


class TraineeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: int
    cohort_id: int | None
    status: str
    onboarding_date: date


class TraineeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cohort_id: int | None = None
    status: str | None = None
    onboarding_date: date | None = None

    @model_validator(mode="after")
    def validate_changes(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        for field in ("status", "onboarding_date"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class TraineeReplace(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cohort_id: int | None
    status: str
    onboarding_date: date


class CohortCreate(BaseModel):
    name: str
    start_date: date
    end_date: date | None


class PlanCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    description: str | None
    due_date: date | None


class ProgressCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trainee_id: int | None = None
    plan_id: int
    status: str
    comments: str | None


class NotificationCreate(BaseModel):
    user_id: int
    message: str
