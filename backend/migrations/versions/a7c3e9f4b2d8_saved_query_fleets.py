"""Saved queries follow any number of fleets, beside the servers they list: `fleet_id` becomes `fleet_ids`

Revision ID: a7c3e9f4b2d8
Revises: f2c8d1a4b6e9
Create Date: 2026-11-20 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7c3e9f4b2d8'
down_revision = 'f2c8d1a4b6e9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('saved_queries', schema=None) as batch_op:
        batch_op.add_column(sa.Column('fleet_ids', sa.JSON(), nullable=True))
    saved = sa.table('saved_queries', sa.column('id', sa.Integer), sa.column('fleet_id', sa.Integer),
                     sa.column('fleet_ids', sa.JSON))
    connection = op.get_bind()
    for savedId, fleetId in connection.execute(sa.select(saved.c.id, saved.c.fleet_id)
                                               .where(saved.c.fleet_id.isnot(None))).all():
        connection.execute(saved.update().where(saved.c.id == savedId).values(fleet_ids=[fleetId]))
    with op.batch_alter_table('saved_queries', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_saved_queries_fleet_id'))
        batch_op.drop_constraint('fk_saved_queries_fleet_id_fleets', type_='foreignkey')
        batch_op.drop_column('fleet_id')


def downgrade():
    """A single fleet without other servers goes back to `fleet_id`; anything else becomes the list of the servers
    it runs on now (the fleets are no longer followed)"""
    with op.batch_alter_table('saved_queries', schema=None) as batch_op:
        batch_op.add_column(sa.Column('fleet_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_saved_queries_fleet_id_fleets', 'fleets', ['fleet_id'], ['id'],
                                    ondelete='SET NULL')
        batch_op.create_index(batch_op.f('ix_saved_queries_fleet_id'), ['fleet_id'], unique=False)
    saved = sa.table('saved_queries', sa.column('id', sa.Integer), sa.column('user_id', sa.Integer),
                     sa.column('fleet_id', sa.Integer), sa.column('fleet_ids', sa.JSON),
                     sa.column('server_ids', sa.JSON))
    servers = sa.table('servers', sa.column('id', sa.Integer), sa.column('name', sa.String),
                       sa.column('fleet_id', sa.Integer), sa.column('user_id', sa.Integer))
    connection = op.get_bind()
    rows = connection.execute(sa.select(saved.c.id, saved.c.user_id, saved.c.fleet_ids, saved.c.server_ids)).all()
    for savedId, userId, fleetIds, serverIds in rows:
        fleetIds, serverIds = fleetIds or [], serverIds or []
        if not fleetIds:
            continue
        if len(fleetIds) == 1 and not serverIds:
            connection.execute(saved.update().where(saved.c.id == savedId).values(fleet_id=fleetIds[0]))
            continue
        listed = []
        for fleetId in fleetIds:
            listed += [row.id for row in connection.execute(
                sa.select(servers.c.id).where(servers.c.fleet_id == fleetId, servers.c.user_id == userId)
                .order_by(servers.c.name, servers.c.id)).all()]
        listed += [serverId for serverId in serverIds if serverId not in listed]
        connection.execute(saved.update().where(saved.c.id == savedId).values(server_ids=listed or None))
    with op.batch_alter_table('saved_queries', schema=None) as batch_op:
        batch_op.drop_column('fleet_ids')
