from functools import wraps
from pathlib import Path
import tomllib
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
import os
import redis
from huey import PriorityRedisHuey
from flask_socketio import SocketIO

MONITORING_SYSTEM = None
MONITORING_SYSTEM_AVAILABLE = False
MONITORING_UNAVAILABLE_REASON = None
try:
    from application.monitoring.monitor import monitor
    from application.monitoring.config import INFLUXDB_TOKEN
    if INFLUXDB_TOKEN is None:
        MONITORING_UNAVAILABLE_REASON = "Monitoring system is disabled: INFLUXDB_TOKEN is not set."
    else:
        MONITORING_SYSTEM = monitor
        MONITORING_SYSTEM_AVAILABLE = True
except ImportError:
    MONITORING_UNAVAILABLE_REASON = "Monitoring system is disabled due to missing libraries."
if MONITORING_UNAVAILABLE_REASON is not None:
    print(MONITORING_UNAVAILABLE_REASON)


class FlaskRedisHuey(PriorityRedisHuey):

    def __init__(self, *args, flaskApp, **kwargs):
        super().__init__(*args, **kwargs)
        self.flaskApp = flaskApp

    def task(self, *args, **kwargs):
        original_task_decorator = super().task(*args, **kwargs)

        def wrapper(fn):
            @wraps(fn)
            def wrapped_task(*fn_args, **fn_kwargs):
                with self.flaskApp.app_context():
                    return fn(*fn_args, **fn_kwargs)

            return original_task_decorator(wrapped_task)
        return wrapper

    def periodic_task(self, *args, **kwargs):
        original_periodic_task_decorator = super().periodic_task(*args, **kwargs)

        def wrapper(fn):
            @wraps(fn)
            def wrapped_task(*fn_args, **fn_kwargs):
                with self.flaskApp.app_context():
                    return fn(*fn_args, **fn_kwargs)

            return original_periodic_task_decorator(wrapped_task)
        return wrapper


# naming_convention = {
#     "ix": 'ix_%(column_0_label)s',
#     "uq": "uq_%(table_name)s_%(column_0_name)s",
#     "ck": "ck_%(table_name)s_%(column_0_name)s",
#     "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
#     "pk": "pk_%(table_name)s"
# }
# db = SQLAlchemy(metadata=MetaData(naming_convention=naming_convention))
db = None
migrate = Migrate()
loadedPlugins = None
flaskApp = None
redisClient = redis.Redis(host=os.environ.get('REDIS_URL', 'localhost'), port=int(os.environ.get('REDIS_PORT', 6380)), db=int(os.environ.get('REDIS_DB', 1)), decode_responses=True)
huey_app = None
socketioApp = None
bcrypt = None
all_user_settings = []
script_dir = Path(__file__).resolve().parent
relative_path = Path('user-settings.toml')
with open(script_dir / relative_path, 'rb') as f:
    all_user_settings = tomllib.load(f)


ENCRYPTED_COLUMNS = (('servers', 'authkey_enc'), ('jobs', 'params_enc'))


def sampleEncryptedAuthkey():
    """An encrypted value from the database (a server authkey, else job parameters), to check the encryption key
    against. None when there is none, including before the migrations introducing these columns have run."""
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)
    for table, column in ENCRYPTED_COLUMNS:
        if not inspector.has_table(table):
            continue
        if column not in {existing['name'] for existing in inspector.get_columns(table)}:
            continue
        with db.engine.connect() as connection:
            sample = connection.execute(text(f'SELECT {column} FROM {table} WHERE {column} IS NOT NULL LIMIT 1')).scalar()
        if sample is not None:
            return sample
    return None


def socketOriginChecker(allowedOrigins):
    """socket.io accepts the origin serving the UI and the configured ones. Only hosts are compared for the
    serving origin, so that TLS-terminating proxies that do not forward the scheme keep working."""
    from urllib.parse import urlsplit

    def isAllowed(origin, environ):
        if origin in allowedOrigins:
            return True
        servingHosts = {environ.get('HTTP_HOST'), (environ.get('HTTP_X_FORWARDED_HOST') or '').split(',')[0].strip()}
        return urlsplit(origin or '').netloc in servingHosts - {None, ''}
    return isAllowed


def trustProxies(app):
    """Trust the X-Forwarded-* headers set by the configured number of reverse proxies"""
    value = str(app.config.get('TRUSTED_PROXIES') or '0').strip()
    try:
        count = int(value)
    except ValueError:
        count = -1
    if count < 0:
        raise RuntimeError(f'TRUSTED_PROXIES must be the number of reverse proxies in front of the application '
                           f'(0 when there is none), not "{value}"')
    if count > 0:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=count, x_proto=count, x_host=count, x_port=count)
    return count


def create_app():
    """Construct the core application."""

    global loadedPlugins, flaskApp, socketioApp, bcrypt, db, migrate
    flaskApp = Flask(__name__, instance_relative_config=False)
    flaskApp.config.from_object(os.environ.get('FLASK_CONFIG', 'config.ProductionConfig'))
    if not flaskApp.config.get('SECRET_KEY'):
        from application import crypto
        flaskApp.config['SECRET_KEY'] = crypto.readOrCreateSecretKey(Path(flaskApp.config['SECRET_KEY_FILE']))
    bcrypt = Bcrypt(flaskApp)

    from application.DBModels import db as sqla_db
    db = sqla_db

    allowedOrigins = flaskApp.config['CORS_ALLOWED_ORIGINS']
    CORS(flaskApp, resources={
        # The browser extension enrolls servers from any origin (MISP pages, its own pages).
        # It authenticates with the Authorization header, which other pages do not have.
        r'/fleets/index': {'origins': '*'},
        r'/servers/add/*': {'origins': '*'},
        r'/users/view/me': {'origins': '*'},
        r'/*': {'origins': allowedOrigins},
    })
    db.init_app(flaskApp)

    migrate.init_app(flaskApp, db)
    huey_app = FlaskRedisHuey(flaskApp.name, url=os.environ.get('WORKER_BROKER_URL', 'redis://localhost:6380/1'), flaskApp=flaskApp)
    flaskApp.extensions["huey"] = huey_app

    from application.plugins import loadAvailablePlugins
    loadedPlugins = loadAvailablePlugins()

    with flaskApp.app_context():
        # Fails here, with an explicit message, if the key is missing or wrong rather than at first use
        from application import crypto
        crypto.init(flaskApp, sampleEncryptedAuthkey)

        socketioApp = SocketIO(
            flaskApp,
            cors_allowed_origins=socketOriginChecker(allowedOrigins),
            message_queue=os.environ.get(
                "SOCKETIO_MESSAGE_QUEUE",
                f"redis://localhost:{str(os.environ.get('REDIS_PORT', 6380))}/3",
            ),
        )
        # Wraps socket.io too, so that its handshakes also see the client behind the proxies
        trustProxies(flaskApp)

        # Imports
        from . import routes
        from application.controllers.users import BPuser
        from application.controllers.userSettings import BPuserSetting
        from application.controllers.servers import BPserver
        from application.controllers.fleets import BPfleet
        from application.controllers.plugins import BPplugins
        from application.controllers.instance import BPinstance
        from application.controllers.pinLists import BPpinLists
        from application.controllers.serverManagement import BPserverManagement
        from application.controllers.health import BPhealth
        from application.controllers.jobs import BPjobs
        from application.controllers.baselines import BPbaselines
        from application.controllers.websocket import registerListeners as registerWSListeners

        flaskApp.register_blueprint(BPuser)
        flaskApp.register_blueprint(BPuserSetting)
        flaskApp.register_blueprint(BPserver)
        flaskApp.register_blueprint(BPfleet)
        flaskApp.register_blueprint(BPplugins)
        flaskApp.register_blueprint(BPpinLists)
        flaskApp.register_blueprint(BPinstance)
        flaskApp.register_blueprint(BPserverManagement)
        flaskApp.register_blueprint(BPhealth)
        flaskApp.register_blueprint(BPjobs)
        flaskApp.register_blueprint(BPbaselines)
        registerWSListeners()

        from application.compression import compressResponse
        flaskApp.after_request(compressResponse)

        # Add CLI commands
        from application.cli import server_cli, user_cli, security_cli

        flaskApp.cli.add_command(server_cli)
        flaskApp.cli.add_command(user_cli)
        flaskApp.cli.add_command(security_cli)

        # Create tables for our models
        from application.DBModels import init_defaults
        # db.create_all()
        # init_defaults()

        return flaskApp
