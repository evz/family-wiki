"""Add configurable chunk settings to TextCorpus

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-07-27 16:30:00.000000

"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6g7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # ### Add query_chunk_limit column to text_corpora table ###
    with op.batch_alter_table('text_corpora', schema=None) as batch_op:
        batch_op.add_column(sa.Column('query_chunk_limit', sa.Integer(), nullable=True))

    # ### Set default values for existing corpora ###
    op.execute("UPDATE text_corpora SET query_chunk_limit = 20 WHERE query_chunk_limit IS NULL")
    op.execute("UPDATE text_corpora SET chunk_size = 1500 WHERE chunk_size = 1000")  # Update old default
    # ### end Alembic commands ###


def downgrade():
    # ### Drop the query_chunk_limit column ###
    with op.batch_alter_table('text_corpora', schema=None) as batch_op:
        batch_op.drop_column('query_chunk_limit')
    # ### end Alembic commands ###
