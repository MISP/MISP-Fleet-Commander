"""Add health_acks: users acknowledging health issues

Revision ID: b3f6a9d2c7e4
Revises: f5b8d1c3a6e2
Create Date: 2026-11-09 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3f6a9d2c7e4'
down_revision = 'f5b8d1c3a6e2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('health_acks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('server_id', sa.Integer(), nullable=False),
    sa.Column('issue_id', sa.String(length=255), nullable=False),
    sa.Column('issue_first_seen', sa.Integer(), nullable=False),
    sa.Column('until', sa.Integer(), nullable=True),
    sa.Column('note', sa.String(length=500), nullable=False),
    sa.Column('created', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'issue_id')
    )
    with op.batch_alter_table('health_acks', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_health_acks_server_id'), ['server_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_health_acks_user_id'), ['user_id'], unique=False)


def downgrade():
    with op.batch_alter_table('health_acks', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_health_acks_user_id'))
        batch_op.drop_index(batch_op.f('ix_health_acks_server_id'))

    op.drop_table('health_acks')
