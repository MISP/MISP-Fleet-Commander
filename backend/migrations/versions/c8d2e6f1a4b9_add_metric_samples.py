"""Add metric_samples and metric_states: usage metrics collected from the servers, kept in the database

Revision ID: c8d2e6f1a4b9
Revises: b81c4f2e9a07
Create Date: 2026-11-18 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c8d2e6f1a4b9'
down_revision = 'b81c4f2e9a07'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('metric_samples',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('server_id', sa.Integer(), nullable=False),
    sa.Column('tier', sa.String(length=8), nullable=False),
    sa.Column('ts', sa.Integer(), nullable=False),
    sa.Column('values', sa.JSON(), nullable=False),
    sa.Column('peaks', sa.JSON(), nullable=True),
    sa.Column('samples', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('server_id', 'tier', 'ts', name='uq_metric_samples_server_tier_ts')
    )
    with op.batch_alter_table('metric_samples', schema=None) as batch_op:
        batch_op.create_index('ix_metric_samples_tier_ts', ['tier', 'ts'], unique=False)

    op.create_table('metric_states',
    sa.Column('server_id', sa.Integer(), autoincrement=False, nullable=False),
    sa.Column('login_cursor', sa.Integer(), nullable=True),
    sa.Column('logins_backfilled', sa.Boolean(), server_default='0', nullable=False),
    sa.Column('logins_read_at', sa.Integer(), nullable=True),
    sa.Column('logins_total', sa.Integer(), server_default='0', nullable=False),
    sa.Column('failed_logins_total', sa.Integer(), server_default='0', nullable=False),
    sa.Column('last_attempt', sa.Integer(), nullable=True),
    sa.Column('last_success', sa.Integer(), nullable=True),
    sa.Column('last_error', sa.String(length=500), nullable=True),
    sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ),
    sa.PrimaryKeyConstraint('server_id')
    )


def downgrade():
    op.drop_table('metric_states')
    with op.batch_alter_table('metric_samples', schema=None) as batch_op:
        batch_op.drop_index('ix_metric_samples_tier_ts')

    op.drop_table('metric_samples')
