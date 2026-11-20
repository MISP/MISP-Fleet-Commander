"""Saved query history: the numbers each server answered to a saved query over time, every answer and one row a day

Revision ID: e6b3f9a2d7c4
Revises: d4a7e2c9f1b3
Create Date: 2026-11-20 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e6b3f9a2d7c4'
down_revision = 'd4a7e2c9f1b3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'saved_query_samples',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('saved_query_id', sa.Integer(), nullable=False),
        sa.Column('server_id', sa.Integer(), nullable=False),
        sa.Column('tier', sa.String(length=8), nullable=False),
        sa.Column('ts', sa.Integer(), nullable=False),
        sa.Column('value', sa.BigInteger(), nullable=False),
        sa.Column('low', sa.BigInteger(), nullable=True),
        sa.Column('high', sa.BigInteger(), nullable=True),
        sa.Column('samples', sa.Integer(), server_default='1', nullable=False),
        sa.Column('more', sa.Boolean(), server_default='0', nullable=False),
        sa.ForeignKeyConstraint(['saved_query_id'], ['saved_queries.id'],
                                name='fk_saved_query_samples_saved_query_id_saved_queries', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['server_id'], ['servers.id'], name='fk_saved_query_samples_server_id_servers',
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('saved_query_id', 'server_id', 'tier', 'ts',
                            name='uq_saved_query_samples_query_server_tier_ts'),
    )
    with op.batch_alter_table('saved_query_samples', schema=None) as batch_op:
        batch_op.create_index('ix_saved_query_samples_tier_ts', ['tier', 'ts'], unique=False)


def downgrade():
    with op.batch_alter_table('saved_query_samples', schema=None) as batch_op:
        batch_op.drop_index('ix_saved_query_samples_tier_ts')
    op.drop_table('saved_query_samples')
