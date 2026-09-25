from datetime import datetime
from typing import Annotated
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, StringConstraints, field_validator
from src.domain.enums import CallDirection, CallStatus


class CallCreate(BaseModel):
    conversation_id: int = Field(gt=0)
    agent_id: int | None = Field(default=None, gt=0)
    direction: CallDirection
    phone_number: str | None = Field(default=None, max_length=32)
    provider: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)] = "manual"
    provider_call_id: str | None = Field(default=None, max_length=255)
    model_config = ConfigDict(extra="forbid")


class CallUpdate(BaseModel):
    status: CallStatus | None = None
    recording_url: AnyHttpUrl | None = Field(default=None, max_length=2048)
    transcript: str | None = Field(default=None, max_length=100000)
    model_config = ConfigDict(extra="forbid")

    @field_validator("status")
    @classmethod
    def not_null(cls, value):
        if value is None:
            raise ValueError("Status cannot be null")
        return value


class CallResponse(BaseModel):
    id: int
    conversation_id: int
    agent_id: int | None
    direction: CallDirection
    status: CallStatus
    phone_number: str | None
    provider: str
    provider_call_id: str | None
    started_at: datetime
    answered_at: datetime | None
    ended_at: datetime | None
    duration_seconds: int
    recording_url: str | None
    transcript: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
