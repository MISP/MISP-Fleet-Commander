"""Add jobs and job_results: writes sent to servers and their per-server outcome

Revision ID: 89f84aee59fc
Revises: b3f6a9d2c7e4
Create Date: 2026-11-09 13:58:48.435093

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '89f84aee59fc'
down_revision = 'b3f6a9d2c7e4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('jobs',
    sa.Column('id', sa.CHAR(length=36), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('user_email', sa.String(length=80), nullable=False),
    sa.Column('fleet_id', sa.Integer(), nullable=True),
    sa.Column('fleet_name', sa.String(length=120), nullable=False),
    sa.Column('kind', sa.String(length=32), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('params', sa.JSON(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('total', sa.Integer(), nullable=False),
    sa.Column('succeeded', sa.Integer(), nullable=False),
    sa.Column('failed', sa.Integer(), nullable=False),
    sa.Column('created', sa.Float(), nullable=False),
    sa.Column('started', sa.Float(), nullable=True),
    sa.Column('finished', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['fleet_id'], ['fleets.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_jobs_created'), ['created'], unique=False)
        batch_op.create_index(batch_op.f('ix_jobs_fleet_id'), ['fleet_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_jobs_kind'), ['kind'], unique=False)
        batch_op.create_index(batch_op.f('ix_jobs_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_jobs_user_id'), ['user_id'], unique=False)

    op.create_table('job_results',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('job_id', sa.CHAR(length=36), nullable=False),
    sa.Column('server_id', sa.Integer(), nullable=True),
    sa.Column('server_name', sa.String(length=120), nullable=False),
    sa.Column('server_url', sa.String(length=256), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('http_status', sa.Integer(), nullable=True),
    sa.Column('summary', sa.String(length=1024), nullable=False),
    sa.Column('response', sa.JSON(), nullable=True),
    sa.Column('response_truncated', sa.Boolean(), server_default='0', nullable=False),
    sa.Column('before', sa.JSON(), nullable=True),
    sa.Column('started', sa.Float(), nullable=True),
    sa.Column('finished', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('job_results', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_job_results_job_id'), ['job_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_job_results_server_id'), ['server_id'], unique=False)


def downgrade():
    with op.batch_alter_table('job_results', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_job_results_server_id'))
        batch_op.drop_index(batch_op.f('ix_job_results_job_id'))

    op.drop_table('job_results')
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_jobs_user_id'))
        batch_op.drop_index(batch_op.f('ix_jobs_status'))
        batch_op.drop_index(batch_op.f('ix_jobs_kind'))
        batch_op.drop_index(batch_op.f('ix_jobs_fleet_id'))
        batch_op.drop_index(batch_op.f('ix_jobs_created'))

    op.drop_table('jobs')
