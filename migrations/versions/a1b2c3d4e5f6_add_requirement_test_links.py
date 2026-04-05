"""add requirement_test_links table

Revision ID: a1b2c3d4e5f6
Revises: e6c9e3df2b02
Create Date: 2026-04-05 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'e6c9e3df2b02'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'requirement_test_links',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('requirement_id', sa.String(length=36), nullable=True),
        sa.Column('user_story_id', sa.String(length=36), nullable=True),
        sa.Column('acceptance_test_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['requirement_id'], ['documents.id']),
        sa.ForeignKeyConstraint(['user_story_id'], ['documents.id']),
        sa.ForeignKeyConstraint(['acceptance_test_id'], ['documents.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('requirement_test_links')
