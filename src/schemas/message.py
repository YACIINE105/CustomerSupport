from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints

from src.domain.enums import MessageSenderType, MessageType


class MessageCreate(BaseModel):
    sender_type: Literal[MessageSenderType.CUSTOMER] = MessageSenderType.CUSTOMER
    sender_id: int = Field(gt=0)
    content: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)]
    message_type: Literal[MessageType.TEXT] = MessageType.TEXT
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_type: MessageSenderType
    sender_id: int | None
    content: str
    message_type: MessageType
    metadata: dict[str, JsonValue] = Field(validation_alias="message_metadata")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
