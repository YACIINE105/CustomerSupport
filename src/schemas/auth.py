from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator

from src.domain.enums import UserRole


class EmailInput(BaseModel):
    email: EmailStr
    model_config = ConfigDict(extra="forbid")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class UserCreate(EmailInput):
    password: SecretStr = Field(min_length=12, max_length=128)
    role: UserRole = UserRole.AGENT


class LoginRequest(EmailInput):
    password: SecretStr = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None
    model_config = ConfigDict(extra="forbid")

    @field_validator("role", "is_active")
    @classmethod
    def reject_explicit_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value
