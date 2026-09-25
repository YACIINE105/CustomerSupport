from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from src.core.database import Base
from src.domain.enums import CallDirection, CallStatus


class Call(Base):
    __tablename__ = "calls"
    __table_args__ = (CheckConstraint("duration_seconds >= 0", name="ck_calls_duration_nonnegative"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), nullable=False, unique=True)
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    direction: Mapped[CallDirection] = mapped_column(Enum(CallDirection, name="call_direction", native_enum=False, create_constraint=True), nullable=False)
    status: Mapped[CallStatus] = mapped_column(Enum(CallStatus, name="call_status", native_enum=False, create_constraint=True), nullable=False, server_default="INITIATED")
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False, server_default="manual")
    provider_call_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    recording_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
