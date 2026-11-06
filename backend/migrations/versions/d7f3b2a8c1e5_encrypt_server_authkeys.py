"""Encrypt the MISP authkeys of servers

Revision ID: d7f3b2a8c1e5
Revises: c4e1a7d2b9f0
Create Date: 2026-11-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

from application import crypto


# revision identifiers, used by Alembic.
revision = 'd7f3b2a8c1e5'
down_revision = 'c4e1a7d2b9f0'
branch_labels = None
depends_on = None


def zeroFreedPages():
    """SQLite keeps deleted content in free pages: overwrite it, so no plaintext authkey stays in the file"""
    if op.get_bind().dialect.name == 'sqlite':
        op.execute('PRAGMA secure_delete = ON')


def upgrade():
    zeroFreedPages()
    with op.batch_alter_table('servers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('authkey_enc', sa.Text(), nullable=True))

    connection = op.get_bind()
    servers = sa.table('servers', sa.column('id', sa.Integer), sa.column('authkey', sa.String),
                       sa.column('authkey_enc', sa.Text))
    for serverId, authkey in connection.execute(sa.select(servers.c.id, servers.c.authkey)).fetchall():
        connection.execute(servers.update().where(servers.c.id == serverId).values(
            authkey_enc=crypto.encrypt(authkey) if authkey else None,
            authkey=None,
        ))

    with op.batch_alter_table('servers', schema=None) as batch_op:
        batch_op.drop_column('authkey')


def downgrade():
    with op.batch_alter_table('servers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('authkey', sa.String(length=40), nullable=True))

    connection = op.get_bind()
    servers = sa.table('servers', sa.column('id', sa.Integer), sa.column('authkey', sa.String),
                       sa.column('authkey_enc', sa.Text))
    for serverId, token in connection.execute(sa.select(servers.c.id, servers.c.authkey_enc)).fetchall():
        connection.execute(servers.update().where(servers.c.id == serverId).values(authkey=crypto.decrypt(token)))

    with op.batch_alter_table('servers', schema=None) as batch_op:
        batch_op.drop_column('authkey_enc')
