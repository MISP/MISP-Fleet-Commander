from os import environ
from os import path as osPath


basedir = osPath.abspath(osPath.dirname(__file__))

class Config:
    """Set Flask configuration vars from .env file."""

    # General
    # TESTING = environ.get('TESTING')
    FLASK_DEBUG = environ.get('FLASK_DEBUG')
    FLASK_ENV = environ.get('FLASK_ENV')
    SECRET_KEY = environ.get('SECRET_KEY')

    # Database
    SQLALCHEMY_DATABASE_URI = environ.get('SQLALCHEMY_DATABASE_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = environ.get('SQLALCHEMY_TRACK_MODIFICATIONS')

class ProductionConfig(Config):
    FLASK_DEBUG = False
    FLASK_ENV = environ.get('FLASK_ENV')
    SECRET_KEY = environ.get('SECRET_KEY')

    # Database
    SQLALCHEMY_DATABASE_URI = 'mysql://user@localhost/foo'
    SQLALCHEMY_TRACK_MODIFICATIONS = True

class DevelopmentConfig(Config):
    FLASK_DEBUG = True
    FLASK_ENV = 'development'
    SECRET_KEY = 'secret'

    # Database
    # SQLALCHEMY_DATABASE_URI = 'sqlite:///database3.db'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + osPath.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = True