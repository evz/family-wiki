"""Add hybrid search columns and indices to SourceText

Revision ID: a1b2c3d4e5f6
Revises: 8d8421bf386c
Create Date: 2025-07-27 15:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '8d8421bf386c'
branch_labels = None
depends_on = None


def upgrade():
    # ### Add new columns to source_texts table ###
    with op.batch_alter_table('source_texts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('content_tsvector', TSVECTOR(), nullable=True))
        batch_op.add_column(sa.Column('dm_codes', ARRAY(sa.String()), nullable=True))

    # ### Create additional indexes ###
    # Note: These will be created after the columns are added

    # Enable required PostgreSQL extensions if they don't exist
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # GIN index for trigram similarity using pg_trgm
    op.create_index(
        'idx_source_text_content_gin_trgm',
        'source_texts',
        ['content'],
        unique=False,
        postgresql_using='gin',
        postgresql_ops={'content': 'gin_trgm_ops'}
    )

    # GIN index for full-text search on tsvector
    op.create_index(
        'idx_source_text_tsvector_gin',
        'source_texts',
        ['content_tsvector'],
        unique=False,
        postgresql_using='gin'
    )

    # GIN index for Daitch-Mokotoff codes array overlap
    op.create_index(
        'idx_source_text_dm_codes_gin',
        'source_texts',
        ['dm_codes'],
        unique=False,
        postgresql_using='gin'
    )

    # Create a trigger to automatically populate content_tsvector from content
    op.execute("""
        CREATE OR REPLACE FUNCTION update_content_tsvector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.content_tsvector := to_tsvector('dutch', COALESCE(NEW.content, ''));
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER update_source_text_tsvector
        BEFORE INSERT OR UPDATE OF content ON source_texts
        FOR EACH ROW
        EXECUTE FUNCTION update_content_tsvector();
    """)

    # Update existing rows to populate tsvector
    op.execute("""
        UPDATE source_texts 
        SET content_tsvector = to_tsvector('dutch', COALESCE(content, '')) 
        WHERE content_tsvector IS NULL;
    """)
    # ### end Alembic commands ###


def downgrade():
    # ### Drop trigger and function first ###
    op.execute("DROP TRIGGER IF EXISTS update_source_text_tsvector ON source_texts;")
    op.execute("DROP FUNCTION IF EXISTS update_content_tsvector();")

    # ### Drop indexes ###
    op.drop_index('idx_source_text_dm_codes_gin', table_name='source_texts')
    op.drop_index('idx_source_text_tsvector_gin', table_name='source_texts')
    op.drop_index('idx_source_text_content_gin_trgm', table_name='source_texts')

    # ### Drop columns ###
    with op.batch_alter_table('source_texts', schema=None) as batch_op:
        batch_op.drop_column('dm_codes')
        batch_op.drop_column('content_tsvector')
    # ### end Alembic commands ###
