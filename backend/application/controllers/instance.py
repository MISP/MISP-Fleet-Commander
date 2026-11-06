from functools import wraps
import math
import pathlib
from flask import Blueprint, current_app, request, render_template, make_response, jsonify, send_from_directory
import jwt
import application.models.servers as serverModel
import application.models.users as userModel
import application.models.setting as settingModel
from application.marshmallowSchemas import serversSchema
from application.DBModels import User, db, Server
import os.path
from huey.exceptions import ResultTimeout
import redis

from application.models.auth import create_access_token, get_email_from_token


class AuthenticationError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


def resolve_user(credential: str) -> User:
    """Return the user behind a credential, in the `Authorization` header format: `Bearer <jwt>` or
    `Apikey <key>`. Used by both the REST API and the socket.io connection.
    Raises AuthenticationError if the credential is missing, malformed, expired or unknown."""
    parts = (credential or '').split()
    if len(parts) != 2:
        raise AuthenticationError('Invalid token. Registeration and / or authentication required')
    token_type, token_value = parts
    if token_type.lower() == 'bearer':
        try:
            user = get_current_user(token_value, current_app)
        except jwt.ExpiredSignatureError:
            raise AuthenticationError('Expired token. Reauthentication required.')
        except jwt.InvalidTokenError:
            raise AuthenticationError('Invalid token. Registeration and / or authentication required')
        if not user:
            raise AuthenticationError('Invalid Bearer')
        return user
    if token_type.lower() == 'apikey':
        user = get_current_user_api(token_value)
        if not user:
            raise AuthenticationError('Invalid API Key')
        return user
    raise AuthenticationError('Invalid token. Registeration and / or authentication required')


# What users with a well-known password can still do: see who they are and change it
PASSWORD_CHANGE_ENDPOINTS = {'user.changePassword', 'user.view'}
MIN_PASSWORD_LENGTH = 12


def token_required(f):
    @wraps(f)
    def _verify(*args, **kwargs):
        try:
            user = resolve_user(request.headers.get('Authorization', ''))
        except AuthenticationError as e:
            return jsonify({'message': e.message, 'authenticated': False}), 401
        if user.must_change_password and request.endpoint not in PASSWORD_CHANGE_ENDPOINTS:
            return jsonify({'message': 'You must change your password first', 'authenticated': True,
                            'password_change_required': True}), 403
        return f(user, *args, **kwargs)

    return _verify


def issue_access_token(user):
    """The login response. The UI only needs who is logged in; everything else is fetched with the token"""
    token = create_access_token(user, {
        'user': {'id': user.id, 'email': user.email, 'is_admin': user.is_admin,
                 'must_change_password': user.must_change_password},
    }, current_app)
    return {"access_token": token, "token_type": "bearer"}

def admin_required(f):
    """Like token_required, and the user must be an administrator"""
    @wraps(f)
    @token_required
    def _verify(user, *args, **kwargs):
        if not user.is_admin:
            return jsonify({'message': 'Administrator role required', 'authenticated': True}), 403
        return f(user, *args, **kwargs)

    return _verify


def get_current_user(token, app):
    email = get_email_from_token(token, app)
    user = userModel.getByEmail(email)
    return user

def get_current_user_api(token):
    return User.byAPIKey(token)


def workers_health_check(timeout=2, sid=None):
    """True if a worker answered in time. With a socket `sid`, the worker also replies to that socket"""
    from application.workers.tasks import ping
    try:
        return ping(sid)(blocking=True, timeout=timeout) == 'pong'
    except ResultTimeout:
        return False


BPinstance = Blueprint('instance', __name__)


@BPinstance.route('/', defaults={'path': ''})
@BPinstance.route('/<string:path>')
@BPinstance.route('/<path:path>')
def static_proxy(path):
    basepath = pathlib.Path(__file__).parent.resolve()
    requestedPath = basepath / '../dist/' / path
    if os.path.isfile(requestedPath):
        # If request is made for a file by vue.js for example main.js
        # condition will be true, file will be served from the public directory
        return send_from_directory(basepath / '../dist', path)
    else:
        # Otherwise index.html will be served,
        # vue.js router will handle the rest
        return send_from_directory(basepath / '../dist', "index.html")

@BPinstance.route('/instance/searchAll/<searchtext>', methods=['GET'])
@token_required
def index(user, searchtext):
    servers = serverModel.searchAll(searchtext, user)
    return serversSchema.dump(servers)


LOGIN_MAX_FAILURES = 5
LOGIN_LOCKOUT_SECONDS = 15 * 60


def loginFailuresKey(email):
    return f"login_failures:{request.remote_addr}:{str(email or '').strip().lower()}"


def loginLockedFor(key):
    """Seconds left before this client can try this account again, 0 if it is not locked out"""
    import application
    try:
        if int(application.redisClient.get(key) or 0) >= LOGIN_MAX_FAILURES:
            return max(application.redisClient.ttl(key), 1)
    except redis.RedisError:
        pass
    return 0


def recordLoginFailure(key):
    import application
    try:
        if application.redisClient.incr(key) == 1:
            application.redisClient.expire(key, LOGIN_LOCKOUT_SECONDS)
    except redis.RedisError:
        pass


def clearLoginFailures(key):
    import application
    try:
        application.redisClient.delete(key)
    except redis.RedisError:
        pass


@BPinstance.route('/login', methods=['POST'])
def login():
    credential = request.get_json(silent=True) or {}
    email, password = credential.get('email'), credential.get('password')
    failuresKey = loginFailuresKey(email)
    lockedFor = loginLockedFor(failuresKey)
    if lockedFor:
        minutes = math.ceil(lockedFor / 60)
        return jsonify({'message': f'Too many failed login attempts. Try again in {minutes} minute{"s" if minutes > 1 else ""}.'}), 429

    user = User.authenticate(email, password)
    if user is None:
        recordLoginFailure(failuresKey)
        return jsonify({'message': 'Invalid credential'}), 401
    clearLoginFailures(failuresKey)
    return jsonify(issue_access_token(user))


@BPinstance.route("/instance/settings/index", methods=["GET"])
@token_required
def settingIndex(user):
    return jsonify(settingModel.index())


@BPinstance.route("/instance/settings/get/<setting_name>", methods=["GET"])
@token_required
def settingGet(user, setting_name):
    return jsonify(settingModel.get(setting_name))


@BPinstance.route("/instance/settings/edit/<setting_name>", methods=["POST"])
@admin_required
def settingEdit(user, setting_name):
    setting_value = request.json.get("value")
    return jsonify(settingModel.set(setting_name, setting_value))
