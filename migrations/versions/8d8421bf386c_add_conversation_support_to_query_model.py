"""Add conversation support to Query model

Revision ID: 8d8421bf386c
Revises: 69b28d50d559
Create Date: 2025-07-26 14:57:40.047912

"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = '8d8421bf386c'
down_revision = '69b28d50d559'
branch_labels = None
depends_on = None


def upgrade():
    # Add conversation support fields to queries table
    op.add_column('queries', sa.Column('conversation_id', sa.dialects.postgresql.UUID(), nullable=True))
    op.add_column('queries', sa.Column('message_sequence', sa.Integer(), nullable=True, default=1))

    # Update existing queries to have message_sequence = 1 (they're all standalone)
    op.execute("UPDATE queries SET message_sequence = 1 WHERE message_sequence IS NULL")


def downgrade():
    # Remove conversation support fields
    op.drop_column('queries', 'message_sequence')
    op.drop_column('queries', 'conversation_id')
