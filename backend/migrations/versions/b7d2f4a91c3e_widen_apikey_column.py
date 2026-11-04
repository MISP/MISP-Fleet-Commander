"""Widen apikey column to 64 chars

Revision ID: b7d2f4a91c3e
Revises: 97a9b79324b5
Create Date: 2026-09-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7d2f4a91c3e'
down_revision = '97a9b79324b5'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('apikey',
                              existing_type=sa.String(length=40),
                              type_=sa.String(length=64),
                              existing_nullable=True)


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('apikey',
                              existing_type=sa.String(length=64),
                              type_=sa.String(length=40),
                              existing_nullable=True)
