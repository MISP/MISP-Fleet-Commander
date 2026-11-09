"""Add jobs.params_enc: job parameters as given, encrypted, for the runner and retries

Revision ID: 2fe2343b6b6a
Revises: 89f84aee59fc
Create Date: 2026-11-09 14:22:40.322295

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2fe2343b6b6a'
down_revision = '89f84aee59fc'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('params_enc', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.drop_column('params_enc')

