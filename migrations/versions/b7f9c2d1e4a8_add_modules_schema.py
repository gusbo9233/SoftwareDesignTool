"""add modules schema

Revision ID: b7f9c2d1e4a8
Revises: a1b2c3d4e5f6
Create Date: 2026-04-09 09:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b7f9c2d1e4a8"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "modules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_id", sa.String(length=36), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["parent_id"], ["modules.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_modules_project_id", "modules", ["project_id"], unique=False)
    op.create_index("ix_modules_parent_id", "modules", ["parent_id"], unique=False)
    op.create_index("ix_modules_project_position", "modules", ["project_id", "position"], unique=False)

    op.add_column("documents", sa.Column("module_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_documents_module_id_modules",
        "documents",
        "modules",
        ["module_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_documents_module_id", "documents", ["module_id"], unique=False)


def downgrade():
    op.drop_index("ix_documents_module_id", table_name="documents")
    op.drop_constraint("fk_documents_module_id_modules", "documents", type_="foreignkey")
    op.drop_column("documents", "module_id")

    op.drop_index("ix_modules_project_position", table_name="modules")
    op.drop_index("ix_modules_parent_id", table_name="modules")
    op.drop_index("ix_modules_project_id", table_name="modules")
    op.drop_table("modules")
