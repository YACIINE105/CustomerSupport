"""Create conversations with contact ownership and controlled states."""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("channel", sa.Enum(
            "CHAT", "VOICE", "PHONE", name="conversation_channel",
            native_enum=False, create_constraint=True,
        ), nullable=False),
        sa.Column("status", sa.Enum(
            "OPEN", "IN_PROGRESS", "WAITING", "RESOLVED", "CLOSED", "ESCALATED",
            name="conversation_status", native_enum=False, create_constraint=True,
        ), nullable=False, server_default="OPEN"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_conversations_customer_id", "conversations", ["customer_id"])


def downgrade():
    op.drop_index("ix_conversations_customer_id", table_name="conversations")
    op.drop_table("conversations")
