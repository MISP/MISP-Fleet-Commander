"""Saved queries: MispQL statements kept by a user, run by hand or on a schedule, and each server's last answer

Revision ID: d4a7e2c9f1b3
Revises: c8d2e6f1a4b9
Create Date: 2026-11-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4a7e2c9f1b3'
down_revision = 'c8d2e6f1a4b9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'saved_queries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('description', sa.String(length=500), server_default='', nullable=False),
        sa.Column('statement', sa.Text(), nullable=False),
        sa.Column('fleet_id', sa.Integer(), nullable=True),
        sa.Column('server_ids', sa.JSON(), nullable=True),
        sa.Column('schedule_minutes', sa.Integer(), nullable=True),
        sa.Column('comparator', sa.String(length=8), nullable=True),
        sa.Column('expected', sa.BigInteger(), nullable=True),
        sa.Column('severity', sa.String(length=16), server_default='warning', nullable=False),
        sa.Column('created', sa.Integer(), nullable=False),
        sa.Column('updated', sa.Integer(), nullable=False),
        sa.Column('last_run_at', sa.Integer(), nullable=True),
        sa.Column('last_job_id', sa.CHAR(length=36), nullable=True),
        sa.Column('last_error', sa.String(length=255), server_default='', nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_saved_queries_user_id_users', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['fleet_id'], ['fleets.id'], name='fk_saved_queries_fleet_id_fleets',
                                ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'name', name='uq_saved_queries_user_id_name'),
    )
    with op.batch_alter_table('saved_queries', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_saved_queries_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_saved_queries_fleet_id'), ['fleet_id'], unique=False)

    op.create_table(
        'saved_query_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('saved_query_id', sa.Integer(), nullable=False),
        sa.Column('server_id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.CHAR(length=36), nullable=True),
        sa.Column('outcome', sa.String(length=32), nullable=False),
        sa.Column('value', sa.BigInteger(), nullable=True),
        sa.Column('more', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('message', sa.String(length=500), server_default='', nullable=False),
        sa.Column('checked_at', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['saved_query_id'], ['saved_queries.id'],
                                name='fk_saved_query_results_saved_query_id_saved_queries', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['server_id'], ['servers.id'], name='fk_saved_query_results_server_id_servers',
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('saved_query_id', 'server_id', name='uq_saved_query_results_query_server'),
    )
    with op.batch_alter_table('saved_query_results', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_saved_query_results_saved_query_id'), ['saved_query_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_saved_query_results_server_id'), ['server_id'], unique=False)


def downgrade():
    with op.batch_alter_table('saved_query_results', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_saved_query_results_server_id'))
        batch_op.drop_index(batch_op.f('ix_saved_query_results_saved_query_id'))
    op.drop_table('saved_query_results')
    with op.batch_alter_table('saved_queries', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_saved_queries_fleet_id'))
        batch_op.drop_index(batch_op.f('ix_saved_queries_user_id'))
    op.drop_table('saved_queries')
