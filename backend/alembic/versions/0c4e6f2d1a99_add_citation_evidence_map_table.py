"""add citation_evidence_map table

Revision ID: 0c4e6f2d1a99
Revises: 9b31c2f4a7d1
Create Date: 2026-02-14 13:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0c4e6f2d1a99"
down_revision = "9b31c2f4a7d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "citation_evidence_map",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "message_id",
            sa.Integer(),
            sa.ForeignKey("chat_message.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("citation_number", sa.Integer(), nullable=False),
        sa.Column(
            "evidence_record_id",
            sa.Integer(),
            sa.ForeignKey("evidence_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "message_id",
            "citation_number",
            name="uq_citation_evidence_map_message_citation",
        ),
    )

    op.create_index(
        "ix_citation_evidence_map_message_id",
        "citation_evidence_map",
        ["message_id"],
        unique=False,
    )
    op.create_index(
        "ix_citation_evidence_map_evidence_record_id",
        "citation_evidence_map",
        ["evidence_record_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_citation_evidence_map_evidence_record_id",
        table_name="citation_evidence_map",
    )
    op.drop_index("ix_citation_evidence_map_message_id", table_name="citation_evidence_map")
    op.drop_table("citation_evidence_map")
