from os import environ
from os import path as osPath


basedir = osPath.abspath(osPath.dirname(__file__))

class Config:
    """Set Flask configuration vars from .env file."""

    # General
    FLASK_DEBUG = environ.get('FLASK_DEBUG')
    FLASK_ENV = environ.get('FLASK_ENV')
    # Signs the session tokens. When SECRET_KEY is not set, it is read from (or generated into) the secret file,
    # so tokens survive restarts and are shared by all processes
    SECRET_KEY = environ.get('SECRET_KEY') or None
    SECRET_KEY_FILE = environ.get('MFC_SECRET_KEY_FILE') or osPath.join(basedir, 'database', 'secret_key')
    TOKEN_EXPIRATION_MIN = environ.get("TOKEN_EXPIRATION_MIN", 60 * 12)

    # Database
    SQLALCHEMY_DATABASE_URI = environ.get('SQLALCHEMY_DATABASE_URI')

    # Origins, besides the one serving the UI, allowed to call the API and open socket.io connections
    # (e.g. a browser extension). Comma separated, empty by default.
    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in (environ.get('CORS_ALLOWED_ORIGINS') or '').split(',') if origin.strip()]

    # Number of reverse proxies in front of the application. Their X-Forwarded-For/-Proto/-Host/-Port headers are
    # trusted, so that the client address (e.g. for login throttling) is the real one. 0 (default): no proxy.
    TRUSTED_PROXIES = environ.get('TRUSTED_PROXIES') or '0'

    # Key encrypting the MISP authkeys in the database. When MFC_ENCRYPTION_KEY is not set, the key is read
    # from (or, on new installs, generated into) the key file
    ENCRYPTION_KEY = environ.get('MFC_ENCRYPTION_KEY') or None
    ENCRYPTION_KEY_FILE = environ.get('MFC_ENCRYPTION_KEY_FILE') or osPath.join(basedir, 'database', 'encryption_key')


class ProductionConfig(Config):
    FLASK_DEBUG = False
    FLASK_ENV = 'production'

    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + osPath.join(basedir,  environ.get('SQLALCHEMY_DATABASE_URI', 'database/database.db'))


class DevelopmentConfig(Config):
    FLASK_DEBUG = True
    FLASK_ENV = 'development'
    SECRET_KEY = environ.get('SECRET_KEY') or 'secret'
    TOKEN_EXPIRATION_MIN = 60*12

    # SQLALCHEMY_DATABASE_URI = 'sqlite:///' + osPath.join(basedir, 'app.db')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + osPath.join(basedir,  environ.get('SQLALCHEMY_DATABASE_URI', 'app.db'))
    environ['AUTHLIB_INSECURE_TRANSPORT'] = 'true'
