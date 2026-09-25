from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from src.domain.enums import AgentStatus


class AgentCreate(BaseModel):
    user_id: int = Field(gt=0)
    display_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
    department: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)] | None = None
    model_config = ConfigDict(extra="forbid")


class AgentStatusUpdate(BaseModel):
    status: AgentStatus
    model_config = ConfigDict(extra="forbid")


class AgentResponse(BaseModel):
    id: int
    user_id: int
    display_name: str
    department: str | None
    status: AgentStatus
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
