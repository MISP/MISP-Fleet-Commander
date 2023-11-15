from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
import redis
from celery import Celery, Task
from flask_socketio import SocketIO
import socketio

from application.DBModels import init_defaults


def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask,
            broker_url = 'redis://localhost',
            result_backend = 'redis://localhost',
            enable_utc = True,
            include=['application.workers.tasks']
    )
    # celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app


# naming_convention = {
#     "ix": 'ix_%(column_0_label)s',
#     "uq": "uq_%(table_name)s_%(column_0_name)s",
#     "ck": "ck_%(table_name)s_%(column_0_name)s",
#     "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
#     "pk": "pk_%(table_name)s"
# }
# db = SQLAlchemy(metadata=MetaData(naming_convention=naming_convention))
db = None
loadedPlugins = None
flaskApp = None
redisClient = redis.Redis(host='localhost', port=6379, db=1)
celery_app = None
socketioApp = None
bcrypt = None


def create_app():
    """Construct the core application."""

    global loadedPlugins, flaskApp, celery_app, socketioApp, bcrypt, db
    flaskApp = Flask(__name__, instance_relative_config=False)
    flaskApp.config.from_object('config.DevelopmentConfig')
    bcrypt = Bcrypt(flaskApp)

    from application.DBModels import db as sqla_db
    db = sqla_db

    CORS(flaskApp)
    migrate = Migrate(flaskApp, db)
    migrate.init_app(flaskApp, db, render_as_batch=True)
    db.init_app(flaskApp)
    celery_app = celery_init_app(flaskApp)


    from application.plugins import loadAvailablePlugins
    loadedPlugins = loadAvailablePlugins()

    # app.config.from_object('config.Config')
    # app.config.from_object('config.DevelopmentConfig')

    with flaskApp.app_context():

        socketioApp = SocketIO(flaskApp, cors_allowed_origins='*', message_queue='redis://localhost:6379/3')

        # Imports
        from . import routes
        from application.controllers.users import BPuser
        from application.controllers.servers import BPserver
        from application.controllers.serverGroups import BPserverGroup
        from application.controllers.plugins import BPplugins
        from application.controllers.instance import BPinstance
        from application.controllers.pinLists import BPpinLists
        from application.controllers.websocket import registerListeners as registerWSListeners

        flaskApp.register_blueprint(BPuser)
        flaskApp.register_blueprint(BPserver)
        flaskApp.register_blueprint(BPserverGroup)
        flaskApp.register_blueprint(BPplugins)
        flaskApp.register_blueprint(BPpinLists)
        flaskApp.register_blueprint(BPinstance)
        registerWSListeners()

        # Add CLI commands
        from application.cli import server_cli

        flaskApp.cli.add_command(server_cli)

        # Create tables for our models
        db.create_all()
        init_defaults()

        return flaskApp
