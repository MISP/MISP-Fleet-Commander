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
try:
    from application.monitoring.monitor import monitor
    MONITORING_SYSTEM = monitor
    MONITORING_SYSTEM_AVAILABLE = True
except ImportError:
    print("The monitoring system is not avaible due to missing libraries.")


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


def create_app():
    """Construct the core application."""

    global loadedPlugins, flaskApp, socketioApp, bcrypt, db, migrate
    flaskApp = Flask(__name__, instance_relative_config=False)
    flaskApp.config.from_object(os.environ.get('FLASK_CONFIG', 'config.ProductionConfig'))
    bcrypt = Bcrypt(flaskApp)

    from application.DBModels import db as sqla_db
    db = sqla_db

    CORS(flaskApp)
    db.init_app(flaskApp)

    migrate.init_app(flaskApp, db)
    huey_app = FlaskRedisHuey(flaskApp.name, url=os.environ.get('WORKER_BROKER_URL', 'redis://localhost:6380/1'), flaskApp=flaskApp)
    flaskApp.extensions["huey"] = huey_app

    from application.plugins import loadAvailablePlugins
    loadedPlugins = loadAvailablePlugins()

    with flaskApp.app_context():

        socketioApp = SocketIO(
            flaskApp,
            cors_allowed_origins="*",
            message_queue=os.environ.get(
                "SOCKETIO_MESSAGE_QUEUE",
                f"redis://localhost:{str(os.environ.get('REDIS_PORT', 6380))}/3",
            ),
        )

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
        from application.controllers.websocket import registerListeners as registerWSListeners

        flaskApp.register_blueprint(BPuser)
        flaskApp.register_blueprint(BPuserSetting)
        flaskApp.register_blueprint(BPserver)
        flaskApp.register_blueprint(BPfleet)
        flaskApp.register_blueprint(BPplugins)
        flaskApp.register_blueprint(BPpinLists)
        flaskApp.register_blueprint(BPinstance)
        flaskApp.register_blueprint(BPserverManagement)
        registerWSListeners()

        # Add CLI commands
        from application.cli import server_cli, user_cli

        flaskApp.cli.add_command(server_cli)
        flaskApp.cli.add_command(user_cli)

        # Create tables for our models
        from application.DBModels import init_defaults
        # db.create_all()
        # init_defaults()

        return flaskApp
