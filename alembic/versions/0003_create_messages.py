"""Create the ordered conversation message timeline."""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("sender_type", sa.Enum(
            "CUSTOMER", "AGENT", "AI", "SYSTEM", name="message_sender_type",
            native_enum=False, create_constraint=True,
        ), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("message_type", sa.Enum(
            "TEXT", "AUDIO", "SYSTEM", name="message_type",
            native_enum=False, create_constraint=True,
        ), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_messages_conversation_timeline", "messages", ["conversation_id", "created_at", "id"])


def downgrade():
    op.drop_index("ix_messages_conversation_timeline", table_name="messages")
    op.drop_table("messages")
