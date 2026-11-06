"""Store the hash of user API keys instead of the keys

Revision ID: e2a9c4f7b3d1
Revises: d7f3b2a8c1e5
Create Date: 2026-11-06 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

from application.models.auth import hash_API_key


# revision identifiers, used by Alembic.
revision = 'e2a9c4f7b3d1'
down_revision = 'd7f3b2a8c1e5'
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name == 'sqlite':
        op.execute('PRAGMA secure_delete = ON')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('apikey_hash', sa.String(length=64), nullable=True))

    # Existing keys keep working: they are hashed, not revoked
    connection = op.get_bind()
    users = sa.table('users', sa.column('id', sa.Integer), sa.column('apikey', sa.String),
                     sa.column('apikey_hash', sa.String))
    for userId, apikey in connection.execute(sa.select(users.c.id, users.c.apikey)).fetchall():
        connection.execute(users.update().where(users.c.id == userId).values(
            apikey_hash=hash_API_key(apikey) if apikey else None,
            apikey=None,
        ))

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('apikey')
        batch_op.create_index(batch_op.f('ix_users_apikey_hash'), ['apikey_hash'], unique=False)


def downgrade():
    # Hashes cannot be turned back into keys: users generate new API keys after a downgrade
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_apikey_hash'))
        batch_op.add_column(sa.Column('apikey', sa.String(length=40), nullable=True))
        batch_op.drop_column('apikey_hash')
