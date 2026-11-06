"""Add is_admin to users

Revision ID: c4e1a7d2b9f0
Revises: 97a9b79324b5
Create Date: 2026-11-06 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4e1a7d2b9f0'
down_revision = '97a9b79324b5'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_admin', sa.Boolean(), server_default='0', nullable=False))

    # Existing installs keep an administrator: the provisioned admin account, or else the oldest user
    op.execute("UPDATE users SET is_admin = 1 WHERE email = 'admin@admin.test'")
    op.execute(
        "UPDATE users SET is_admin = 1 WHERE id = (SELECT MIN(id) FROM users) "
        "AND NOT EXISTS (SELECT 1 FROM users WHERE is_admin = 1)"
    )


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('is_admin')
