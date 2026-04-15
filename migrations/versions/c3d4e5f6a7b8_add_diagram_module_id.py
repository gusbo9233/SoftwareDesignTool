"""add diagram module id

Revision ID: c3d4e5f6a7b8
Revises: b7f9c2d1e4a8
Create Date: 2026-04-10 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "b7f9c2d1e4a8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("diagrams", sa.Column("module_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_diagrams_module_id_modules",
        "diagrams",
        "modules",
        ["module_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_diagrams_module_id", "diagrams", ["module_id"], unique=False)


def downgrade():
    op.drop_index("ix_diagrams_module_id", table_name="diagrams")
    op.drop_constraint("fk_diagrams_module_id_modules", "diagrams", type_="foreignkey")
    op.drop_column("diagrams", "module_id")
