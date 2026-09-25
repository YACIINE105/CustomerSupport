from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column
from src.core.database import Base
from src.domain.enums import EscalationPriority, EscalationStatus


class Escalation(Base):
    __tablename__ = "escalations"
    __table_args__ = (Index("uq_escalations_active_conversation", "conversation_id", unique=True,
                           postgresql_where=text("status != 'RESOLVED'"), sqlite_where=text("status != 'RESOLVED'")),)
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), nullable=False, index=True)
    assigned_agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    reason: Mapped[str] = mapped_column(String(2000), nullable=False)
    priority: Mapped[EscalationPriority] = mapped_column(Enum(EscalationPriority, name="escalation_priority", native_enum=False, create_constraint=True), nullable=False)
    status: Mapped[EscalationStatus] = mapped_column(Enum(EscalationStatus, name="escalation_status", native_enum=False, create_constraint=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
