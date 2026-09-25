from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.domain.enums import ConversationChannel, ConversationStatus

if TYPE_CHECKING:
    from src.models.customer import Customer


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        nullable=False,
        index=True,
    )

    customer: Mapped["Customer"] = relationship(
        back_populates="conversations",
    )

    channel: Mapped[ConversationChannel] = mapped_column(
        Enum(ConversationChannel, name="conversation_channel", native_enum=False,
             create_constraint=True),
        nullable=False,
    )
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus, name="conversation_status", native_enum=False,
             create_constraint=True),
        nullable=False,
        server_default=ConversationStatus.OPEN.value,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
