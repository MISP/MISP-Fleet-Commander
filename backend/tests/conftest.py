import os
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
def auth_headers(app):
    from application.models.auth import create_access_token

    def _auth_headers(user):
        token = create_access_token(user, {}, app)
        return {"Authorization": f"Bearer {token}"}
    return _auth_headers
