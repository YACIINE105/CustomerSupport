"""Store provider-independent call records."""
from alembic import op
import sqlalchemy as sa
revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("calls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversations.id"), nullable=False, unique=True),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("direction", sa.Enum("INBOUND", "OUTBOUND", name="call_direction", native_enum=False, create_constraint=True), nullable=False),
        sa.Column("status", sa.Enum("INITIATED", "RINGING", "ANSWERED", "COMPLETED", "FAILED", "CANCELLED", "MISSED", name="call_status", native_enum=False, create_constraint=True), nullable=False, server_default="INITIATED"),
        sa.Column("phone_number", sa.String(32), nullable=True),
        sa.Column("provider", sa.String(100), nullable=False, server_default="manual"),
        sa.Column("provider_call_id", sa.String(255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recording_url", sa.String(2048), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("duration_seconds >= 0", name="ck_calls_duration_nonnegative"))


def downgrade():
    op.drop_table("calls")
