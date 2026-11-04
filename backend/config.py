from os import environ
from os import fdopen
from os import makedirs
from os import open as osOpen
from os import path as osPath
from os import O_CREAT, O_EXCL, O_WRONLY
import secrets
from time import sleep


basedir = osPath.abspath(osPath.dirname(__file__))


def getPersistentSecretKey():
    """Return a secret key shared by every process, generating it once on disk.

    The key must be identical in the web application and in the workers,
    otherwise the tokens signed by one process cannot be validated by another.
    """
    keyDir = osPath.join(basedir, 'database')
    keyPath = osPath.join(keyDir, 'secret_key')
    makedirs(keyDir, exist_ok=True)
    for _ in range(10):
        try:
            fd = osOpen(keyPath, O_CREAT | O_EXCL | O_WRONLY, 0o600)
        except FileExistsError:
            pass
        else:
            with fdopen(fd, 'w') as f:
                f.write(secrets.token_hex())
        try:
            with open(keyPath) as f:
                key = f.read().strip()
            if key:
                return key
        except FileNotFoundError:
            pass
        sleep(0.1)
    raise RuntimeError(f'The secret key file {keyPath} is missing or empty')


class Config:
    """Set Flask configuration vars from .env file."""

    # General
    FLASK_DEBUG = environ.get('FLASK_DEBUG')
    FLASK_ENV = environ.get('FLASK_ENV')
    SECRET_KEY = environ.get("SECRET_KEY") or getPersistentSecretKey()
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
