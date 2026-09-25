from datetime import datetime
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator
from src.domain.enums import EscalationPriority, EscalationStatus


class EscalationCreate(BaseModel):
    conversation_id: int = Field(gt=0)
    assigned_agent_id: int | None = Field(default=None, gt=0)
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    priority: EscalationPriority = EscalationPriority.MEDIUM
    model_config = ConfigDict(extra="forbid")


class EscalationUpdate(BaseModel):
    assigned_agent_id: int | None = Field(default=None, gt=0)
    priority: EscalationPriority | None = None
    status: Literal[EscalationStatus.RESOLVED] | None = None
    model_config = ConfigDict(extra="forbid")

    @field_validator("priority", "status")
    @classmethod
    def not_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value


class EscalationResponse(BaseModel):
    id: int
    conversation_id: int
    assigned_agent_id: int | None
    reason: str
    priority: EscalationPriority
    status: EscalationStatus
    created_at: datetime
    resolved_at: datetime | None
    model_config = ConfigDict(from_attributes=True)
