"""Saved baselines: a baseline without a fleet, named and owned by a user, copied into fleets

Revision ID: b81c4f2e9a07
Revises: 6a1d3e9c5b72
Create Date: 2026-11-16 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b81c4f2e9a07'
down_revision = '6a1d3e9c5b72'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('baselines', schema=None) as batch_op:
        batch_op.alter_column('fleet_id', existing_type=sa.Integer(), nullable=True)
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('name', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('description', sa.String(length=500), server_default='', nullable=False))
        batch_op.create_index(batch_op.f('ix_baselines_user_id'), ['user_id'], unique=False)
        batch_op.create_unique_constraint('uq_baselines_user_id_name', ['user_id', 'name'])
        batch_op.create_foreign_key('fk_baselines_user_id_users', 'users', ['user_id'], ['id'], ondelete='CASCADE')


def downgrade():
    # Saved baselines have no fleet: they cannot be kept once `fleet_id` is required again
    op.execute('DELETE FROM baseline_rules WHERE baseline_id IN (SELECT id FROM baselines WHERE fleet_id IS NULL)')
    op.execute('DELETE FROM baselines WHERE fleet_id IS NULL')
    with op.batch_alter_table('baselines', schema=None) as batch_op:
        batch_op.drop_constraint('fk_baselines_user_id_users', type_='foreignkey')
        batch_op.drop_constraint('uq_baselines_user_id_name', type_='unique')
        batch_op.drop_index(batch_op.f('ix_baselines_user_id'))
        batch_op.drop_column('description')
        batch_op.drop_column('name')
        batch_op.drop_column('user_id')
        batch_op.alter_column('fleet_id', existing_type=sa.Integer(), nullable=False)
