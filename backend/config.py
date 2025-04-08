from os import environ
from os import path as osPath
import secrets


basedir = osPath.abspath(osPath.dirname(__file__))

class Config:
    """Set Flask configuration vars from .env file."""

    # General
    FLASK_DEBUG = environ.get('FLASK_DEBUG')
    FLASK_ENV = environ.get('FLASK_ENV')
    SECRET_KEY = environ.get("SECRET_KEY", secrets.token_hex())
    TOKEN_EXPIRATION_MIN = environ.get("TOKEN_EXPIRATION_MIN", 60 * 12)

    # Database
    SQLALCHEMY_DATABASE_URI = environ.get('SQLALCHEMY_DATABASE_URI')

    # Monitoring
    GRAFANA_BASE_URL = environ.get('GRAFANA_BASE_URL', 'http://localhost:3000')
    GRAFANA_DASHBOARD_DATA_RENDER = environ.get('GRAFANA_DASHBOARD_DATA_RENDER', 'render/d-solo/ce6olif96756od')
    GRAFANA_DASHBOARD = environ.get('GRAFANA_DASHBOARD', 'd/ce6olif96756od/circl-monitoring-misp')
    GRAFANA_APIKEY = environ.get('GRAFANA_APIKEY', 'glsa_k94PVSfhraGiK5roLyoniHu0xFyvByne_b1604732')


class ProductionConfig(Config):
    FLASK_DEBUG = False
    FLASK_ENV = 'production'

    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + osPath.join(basedir,  environ.get('SQLALCHEMY_DATABASE_URI', 'database/database.db'))


class DevelopmentConfig(Config):
    FLASK_DEBUG = True
    FLASK_ENV = 'development'
    SECRET_KEY = 'secret'
    TOKEN_EXPIRATION_MIN = 60*12

    # SQLALCHEMY_DATABASE_URI = 'sqlite:///' + osPath.join(basedir, 'app.db')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + osPath.join(basedir,  environ.get('SQLALCHEMY_DATABASE_URI', 'app.db'))
    environ['AUTHLIB_INSECURE_TRANSPORT'] = 'true'
