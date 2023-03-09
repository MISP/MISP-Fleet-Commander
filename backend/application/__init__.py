from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from flask_migrate import Migrate


# naming_convention = {
#     "ix": 'ix_%(column_0_label)s',
#     "uq": "uq_%(table_name)s_%(column_0_name)s",
#     "ck": "ck_%(table_name)s_%(column_0_name)s",
#     "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
#     "pk": "pk_%(table_name)s"
# }
# db = SQLAlchemy(metadata=MetaData(naming_convention=naming_convention))
db = SQLAlchemy()
loadedPlugins = None
app = None


def create_app():
    """Construct the core application."""
    global loadedPlugins, app
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('config.DevelopmentConfig')
    CORS(app)
    migrate = Migrate(app, db)
    migrate.init_app(app, db, render_as_batch=True)
    db.init_app(app)
    from application.plugins import loadAvailablePlugins
    loadedPlugins = loadAvailablePlugins()

    # app.config.from_object('config.Config')
    # app.config.from_object('config.DevelopmentConfig')

    with app.app_context():

        # from application.marshmallowSchemas import setupListener
        # setupListener()

        # Imports
        from . import routes
        from application.controllers.users import BPuser
        from application.controllers.servers import BPserver
        from application.controllers.serverGroups import BPserverGroup
        from application.controllers.plugins import BPplugins
        from application.controllers.instance import BPinstance

        app.register_blueprint(BPuser)
        app.register_blueprint(BPserver)
        app.register_blueprint(BPserverGroup)
        app.register_blueprint(BPplugins)
        app.register_blueprint(BPinstance)

        # Add CLI commands
        from application.cli import server_cli

        app.cli.add_command(server_cli)

        # Create tables for our models
        db.create_all()

        return app
