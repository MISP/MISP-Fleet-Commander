"""Add must_change_password to users

Revision ID: f5b8d1c3a6e2
Revises: e2a9c4f7b3d1
Create Date: 2026-11-06 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import bcrypt


# revision identifiers, used by Alembic.
revision = 'f5b8d1c3a6e2'
down_revision = 'e2a9c4f7b3d1'
branch_labels = None
depends_on = None

# The documented password of the provisioned administrator
DEFAULT_PASSWORD = b'Password1234'


def usesDefaultPassword(hashedPassword):
    # Hashes were stored as text or, for accounts created from the application, as bytes
    if isinstance(hashedPassword, str):
        hashedPassword = hashedPassword.encode()
    try:
        return bcrypt.checkpw(DEFAULT_PASSWORD, hashedPassword)
    except (ValueError, TypeError):
        return False


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('must_change_password', sa.Boolean(), server_default='0', nullable=False))

    # Any account still using the documented password must change it: on new installs, the provisioned administrator
    connection = op.get_bind()
    users = sa.table('users', sa.column('id', sa.Integer), sa.column('hashed_password', sa.String),
                     sa.column('must_change_password', sa.Boolean))
    for userId, hashedPassword in connection.execute(sa.select(users.c.id, users.c.hashed_password)).fetchall():
        values = {}
        if usesDefaultPassword(hashedPassword):
            values['must_change_password'] = True
        if isinstance(hashedPassword, bytes):
            values['hashed_password'] = hashedPassword.decode()
        if values:
            connection.execute(users.update().where(users.c.id == userId).values(**values))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('must_change_password')
