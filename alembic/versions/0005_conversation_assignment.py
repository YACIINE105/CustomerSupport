"""Add human-agent assignment to conversations."""
from alembic import op
import sqlalchemy as sa
revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("conversations") as batch:
        batch.add_column(sa.Column("assigned_agent_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_conversations_agent", "agents", ["assigned_agent_id"], ["id"])
        batch.create_index("ix_conversations_assigned_agent_id", ["assigned_agent_id"])


def downgrade():
    with op.batch_alter_table("conversations") as batch:
        batch.drop_index("ix_conversations_assigned_agent_id")
        batch.drop_constraint("fk_conversations_agent", type_="foreignkey")
        batch.drop_column("assigned_agent_id")
