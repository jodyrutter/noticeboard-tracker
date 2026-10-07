import re
import string
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

MIN_PASSWORD_LENGTH = 8
_ALPHANUMERIC = frozenset(string.ascii_letters + string.digits)
_EMAIL_PATTERN = re.compile(r"^[^\s@]*[A-Za-z][^\s@]*@[^\s@]*[A-Za-z][^\s@]*\.[^\s@]*[A-Za-z][^\s@]*$")


def _validate_password_strength(password: str) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long")
    if all(char in _ALPHANUMERIC for char in password):
        raise ValueError("Password must contain at least one special character")
    return password


def _validate_email_format(email: str) -> str:
    if not _EMAIL_PATTERN.match(email):
        raise ValueError("Must be a valid email address")
    return email


NonBlankString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Role = Literal["TRAINEE", "HR", "MANAGER"]


class SignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
    password: str = Field(min_length=1, max_length=1024, repr=False)

    @field_validator("email")
    @classmethod
    def _email_format(cls, value: str) -> str:
        return _validate_email_format(value)

    @field_validator("password")
    @classmethod
    def _password_strength(cls, value: str) -> str:
        return _validate_password_strength(value)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: NonBlankString
    password: str = Field(min_length=1, max_length=1024, repr=False)


class User(BaseModel):
    user_id: int
    name: str
    email: str
    role: Role


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
