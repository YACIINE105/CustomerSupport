"""Create escalation workflow and prevent duplicate active escalations."""
from alembic import op
import sqlalchemy as sa
revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("escalations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("assigned_agent_id", sa.Integer(), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("reason", sa.String(2000), nullable=False),
        sa.Column("priority", sa.Enum("LOW", "MEDIUM", "HIGH", "URGENT", name="escalation_priority", native_enum=False, create_constraint=True), nullable=False),
        sa.Column("status", sa.Enum("OPEN", "ASSIGNED", "RESOLVED", name="escalation_status", native_enum=False, create_constraint=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_escalations_conversation_id", "escalations", ["conversation_id"])
    op.create_index("uq_escalations_active_conversation", "escalations", ["conversation_id"], unique=True,
                    postgresql_where=sa.text("status != 'RESOLVED'"), sqlite_where=sa.text("status != 'RESOLVED'"))


def downgrade():
    op.drop_table("escalations")
