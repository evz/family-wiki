"""Add genealogical context fields to SourceText model

Revision ID: 834f49f974c7
Revises: b2c3d4e5f6g7
Create Date: 2025-07-29 07:14:52.348128

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '834f49f974c7'
down_revision = 'b2c3d4e5f6g7'
branch_labels = None
depends_on = None


def upgrade():
    # Add genealogical context fields to source_texts table
    op.add_column('source_texts', sa.Column('generation_number', sa.Integer(), nullable=True))
    op.add_column('source_texts', sa.Column('generation_text', sa.String(length=100), nullable=True))
    op.add_column('source_texts', sa.Column('family_context', sa.JSON(), nullable=True))
    op.add_column('source_texts', sa.Column('birth_years', sa.ARRAY(sa.Integer()), nullable=True))
    op.add_column('source_texts', sa.Column('chunk_type', sa.String(length=50), nullable=True))


def downgrade():
    # Remove genealogical context fields from source_texts table
    op.drop_column('source_texts', 'chunk_type')
    op.drop_column('source_texts', 'birth_years')
    op.drop_column('source_texts', 'family_context')
    op.drop_column('source_texts', 'generation_text')
    op.drop_column('source_texts', 'generation_number')
