import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "test.db"
    os.environ["FLASK_CONFIG"] = "config.DevelopmentConfig"
    os.environ["SQLALCHEMY_DATABASE_URI"] = str(db_path)
    # No message queue: socket.io runs in memory, so tests can connect clients and observe emitted events
    os.environ["SOCKETIO_MESSAGE_QUEUE"] = ""
    from cryptography.fernet import Fernet
    os.environ["MFC_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    os.environ["MFC_ENCRYPTION_KEY_FILE"] = str(db_path.parent / "encryption_key")
    os.environ["CORS_ALLOWED_ORIGINS"] = "https://extension.test"

    # Keep the app's data off any real Redis: swap the shared client before models import it
    import fakeredis
    import application
    application.redisClient = fakeredis.FakeRedis(decode_responses=True)

    # The workers' task module builds the app when imported: use that app, so that there is a single app
    # (and a single socket.io server) in the test session
    from application.workers import tasks
    flaskApp = tasks.flaskApp
    flaskApp.config["TESTING"] = True
    with flaskApp.app_context():
        application.db.create_all()
        yield flaskApp


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    from application import db as sqla_db
    yield sqla_db
    sqla_db.session.rollback()


@pytest.fixture()
def make_user(db):
    from application.DBModels import User

    def _make_user(email, is_admin=False):
        user = User.query.filter_by(email=email).first()
        if user is None:
            user = User(email=email, password="Password1234", is_admin=is_admin)
            db.session.add(user)
            db.session.commit()
        return user
    return _make_user


@pytest.fixture()
def flask_cli(tmp_path):
    """Runs `flask` commands in a subprocess, against a database and a key file of its own (to test migrations)"""
    class FlaskCLI:
        db_path = tmp_path / "cli.db"
        key_file = tmp_path / "encryption_key"
        env = dict(os.environ, FLASK_APP="wsgi.py", FLASK_CONFIG="config.DevelopmentConfig",
                   SQLALCHEMY_DATABASE_URI=str(tmp_path / "cli.db"), SOCKETIO_MESSAGE_QUEUE="",
                   MFC_ENCRYPTION_KEY="", MFC_ENCRYPTION_KEY_FILE=str(tmp_path / "encryption_key"))

        def run(self, *args, **env):
            result = subprocess.run([sys.executable, "-m", "flask", *args], cwd=BACKEND_DIR, env=dict(self.env, **env),
                                    capture_output=True, text=True, timeout=120)
            return result

        def python(self, code, **env):
            return subprocess.run([sys.executable, "-c", code], cwd=BACKEND_DIR, env=dict(self.env, **env),
                                  capture_output=True, text=True, timeout=120)

        def upgrade(self, revision="head"):
            result = self.run("db", "upgrade", revision)
            assert result.returncode == 0, result.stderr
    return FlaskCLI()


@pytest.fixture()
def socket_client(app):
    """Connects in-memory socket.io clients, as a user or with a raw token"""
    from application import socketioApp
    from application.models.auth import create_access_token
    clients = []

    def _connect(user=None, token=None):
        if user is not None:
            token = create_access_token(user, {}, app)
        auth = {"token": token} if token is not None else None
        client = socketioApp.test_client(app, auth=auth)
        clients.append(client)
        return client
    yield _connect
    for client in clients:
        if client.is_connected():
            client.disconnect()


@pytest.fixture()
def auth_headers(app):
    from application.models.auth import create_access_token

    def _auth_headers(user):
        token = create_access_token(user, {}, app)
        return {"Authorization": f"Bearer {token}"}
    return _auth_headers
