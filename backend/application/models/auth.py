
import jwt
from datetime import datetime, timedelta
from application.DBModels import User


def create_access_token(user, data, currentApp):
    token = jwt.encode({
        'sub': user.email,
        'iat':datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(minutes=currentApp.config['TOKEN_EXPIRATION_MIN']),
        'data': data,
        },
        currentApp.config['SECRET_KEY'],
        algorithm="HS256"
    )
    return token


def get_current_user(token, currentApp):
    data = jwt.decode(token, currentApp.config['SECRET_KEY'], algorithms=["HS256"])
    email = data.get('sub')
    user = User.query.filter_by(email=email).first()
    return user
