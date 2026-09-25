from typing import TYPE_CHECKING

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship


from src.core.database import Base

if TYPE_CHECKING:
    from src.models.conversation import Conversation


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), index=True)
    phone: Mapped[str | None] = mapped_column(String(32), index=True)
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
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="customer",
        passive_deletes="all",
    )
