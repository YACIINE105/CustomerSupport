from datetime import datetime
from src.domain.enums import ConversationChannel, ConversationStatus

from pydantic import BaseModel, ConfigDict, Field

class ConversationCreate(BaseModel):
    customer_id : int = Field(gt=0)
    channel: ConversationChannel

    model_config = ConfigDict(extra="forbid")


class ConversationResponse(BaseModel):
    id : int
    customer_id:int
    assigned_agent_id: int | None

    channel: ConversationChannel
    status: ConversationStatus

    started_at:datetime
    ended_at: datetime | None
    created_at: datetime
    updated_at:datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationUpdate(BaseModel):
    status: ConversationStatus
    model_config = ConfigDict(extra="forbid")


class ConversationAssign(BaseModel):
    agent_id: int = Field(gt=0)
    model_config = ConfigDict(extra="forbid")
