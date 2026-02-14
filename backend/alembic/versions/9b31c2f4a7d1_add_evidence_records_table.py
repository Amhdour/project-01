"""add evidence_records table

Revision ID: 9b31c2f4a7d1
Revises: 73e9983e5091
Create Date: 2026-02-14 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "9b31c2f4a7d1"
down_revision = "73e9983e5091"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evidence_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.String(), nullable=False),
        sa.Column(
            "chat_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_session.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "message_id",
            sa.Integer(),
            sa.ForeignKey("chat_message.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_uri", sa.String(), nullable=True),
        sa.Column("chunk_id", sa.String(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
    )

    op.create_index(
        "ix_evidence_records_request_id", "evidence_records", ["request_id"], unique=False
    )
    op.create_index(
        "ix_evidence_records_chat_session_id",
        "evidence_records",
        ["chat_session_id"],
        unique=False,
    )
    op.create_index(
        "ix_evidence_records_message_id", "evidence_records", ["message_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_evidence_records_message_id", table_name="evidence_records")
    op.drop_index("ix_evidence_records_chat_session_id", table_name="evidence_records")
    op.drop_index("ix_evidence_records_request_id", table_name="evidence_records")
    op.drop_table("evidence_records")
