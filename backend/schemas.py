from datetime import date
from typing import Literal
from auth_models import Role

from pydantic import BaseModel, ConfigDict, Field, model_validator


TraineeStatus = Literal["ACTIVE", "INACTIVE", "COMPLETED", "WITHDRAWN"]
ProgressStatus = Literal["NOT_STARTED", "IN_PROGRESS", "COMPLETED", "BLOCKED"]


class RoleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Role


class TraineeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: int
    cohort_id: int | None
    status: TraineeStatus
    onboarding_date: date


class TraineeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cohort_id: int | None = None
    status: TraineeStatus | None = None
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
    status: TraineeStatus
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
    status: ProgressStatus
    comments: str | None


class NotificationCreate(BaseModel):
    user_id: int
    message: str


class CohortMembersUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    add: list[int] = Field(default_factory=list, max_length=1000)
    remove: list[int] = Field(default_factory=list, max_length=1000)

    @model_validator(mode="after")
    def validate_members(self):
        if set(self.add) & set(self.remove):
            raise ValueError("A trainee cannot be added and removed together")
        if any(i <= 0 for i in self.add + self.remove):
            raise ValueError("Trainee IDs must be positive")
        return self
