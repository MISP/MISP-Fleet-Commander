
import hashlib
import jwt
from datetime import datetime, timedelta
import secrets


def create_access_token(user, data, currentApp):
    token = jwt.encode({
        'sub': user.email,
        'iat':datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(minutes=int(currentApp.config['TOKEN_EXPIRATION_MIN'])),
        'data': data,
        },
        currentApp.config['SECRET_KEY'],
        algorithm="HS256"
    )
    return token


def create_API_key():
    apikey = secrets.token_urlsafe(40)
    return apikey


def hash_API_key(apikey: str) -> str:
    """API keys are random and long: a fast hash is enough, and it allows looking keys up"""
    return hashlib.sha256(apikey.encode()).hexdigest()


def get_email_from_token(token, currentApp):
    data = jwt.decode(token, currentApp.config['SECRET_KEY'], algorithms=["HS256"])
    email = data.get('sub')
    return email
