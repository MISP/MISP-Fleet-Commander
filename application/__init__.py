from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate


db = SQLAlchemy()


def create_app():
    """Construct the core application."""
    app = Flask(__name__, instance_relative_config=False)
    CORS(app)
    migrate = Migrate(app, db)
    db.init_app(app)
    # app.config.from_object('config.Config')
    app.config.from_object('config.DevelopmentConfig')

    with app.app_context():
        # Imports
        from . import routes
        from application.controllers.users import BPuser
        from application.controllers.servers import BPserver

        app.register_blueprint(BPuser)
        app.register_blueprint(BPserver)

        # Create tables for our models
        db.create_all()

        return app