"""Usage widgets: saved queries followed on a fleet's Usage tab, summed over the fleet or server by server

Revision ID: f2c8d1a4b6e9
Revises: e6b3f9a2d7c4
Create Date: 2026-11-20 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f2c8d1a4b6e9'
down_revision = 'e6b3f9a2d7c4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'usage_widgets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('fleet_id', sa.Integer(), nullable=False),
        sa.Column('kind', sa.String(length=32), server_default='saved_query', nullable=False),
        sa.Column('saved_query_id', sa.Integer(), nullable=True),
        sa.Column('display', sa.String(length=16), server_default='total', nullable=False),
        sa.Column('position', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['fleet_id'], ['fleets.id'], name='fk_usage_widgets_fleet_id_fleets',
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['saved_query_id'], ['saved_queries.id'],
                                name='fk_usage_widgets_saved_query_id_saved_queries', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('fleet_id', 'saved_query_id', name='uq_usage_widgets_fleet_saved_query'),
    )
    with op.batch_alter_table('usage_widgets', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_usage_widgets_fleet_id'), ['fleet_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_usage_widgets_saved_query_id'), ['saved_query_id'], unique=False)


def downgrade():
    with op.batch_alter_table('usage_widgets', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_usage_widgets_saved_query_id'))
        batch_op.drop_index(batch_op.f('ix_usage_widgets_fleet_id'))
    op.drop_table('usage_widgets')
