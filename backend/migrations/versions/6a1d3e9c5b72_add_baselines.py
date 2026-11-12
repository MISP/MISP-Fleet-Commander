"""Add baselines and baseline_rules: the configuration a fleet's servers are expected to have

Revision ID: 6a1d3e9c5b72
Revises: 2fe2343b6b6a
Create Date: 2026-11-12 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6a1d3e9c5b72'
down_revision = '2fe2343b6b6a'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('baselines',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('fleet_id', sa.Integer(), nullable=False),
    sa.Column('created', sa.Integer(), nullable=False),
    sa.Column('updated', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['fleet_id'], ['fleets.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('fleet_id')
    )
    op.create_table('baseline_rules',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('baseline_id', sa.Integer(), nullable=False),
    sa.Column('type', sa.String(length=32), nullable=False),
    sa.Column('key', sa.String(length=255), nullable=False),
    sa.Column('label', sa.String(length=255), nullable=False),
    sa.Column('expected', sa.JSON(), nullable=True),
    sa.Column('comparator', sa.String(length=8), nullable=False),
    sa.Column('severity', sa.String(length=16), nullable=False),
    sa.Column('note', sa.String(length=500), nullable=False),
    sa.Column('forced', sa.Boolean(), server_default='0', nullable=False),
    sa.Column('created', sa.Integer(), nullable=False),
    sa.Column('updated', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['baseline_id'], ['baselines.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('baseline_id', 'type', 'key')
    )
    with op.batch_alter_table('baseline_rules', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_baseline_rules_baseline_id'), ['baseline_id'], unique=False)


def downgrade():
    with op.batch_alter_table('baseline_rules', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_baseline_rules_baseline_id'))

    op.drop_table('baseline_rules')
    op.drop_table('baselines')
