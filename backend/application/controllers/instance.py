from functools import wraps
import pathlib
from flask import Blueprint, current_app, request, render_template, make_response, jsonify, send_from_directory
from flask import session, abort
import jwt
import application.models.servers as serverModel
import application.models.users as userModel
import application.models.setting as settingModel
from application.marshmallowSchemas import userSchema, serversSchema
from application.DBModels import User, db, Server
import os.path
from huey.exceptions import ResultTimeout

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


def token_required(f):
    @wraps(f)
    def _verify(*args, **kwargs):
        try:
            user = resolve_user(request.headers.get('Authorization', ''))
        except AuthenticationError as e:
            return jsonify({'message': e.message, 'authenticated': False}), 401
        return f(user, *args, **kwargs)

    return _verify

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
    user = User.query.filter_by(apikey=token).first()
    return user


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


@BPinstance.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        email = request.json.get('email')
        password = request.json.get('password')
        user = User.authenticate(email, password)
        if user is None:
            abort(401, description="Invalid credential")

        scopes = ['test']
        token = create_access_token(user, {
            'user': userSchema.dump(user), 
            'scopes': scopes, 
        }, current_app)
        return jsonify({"access_token": token, "token_type": "bearer"})
    return jsonify(), 404


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
