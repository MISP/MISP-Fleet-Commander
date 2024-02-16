
from functools import wraps
import pathlib
from flask import Blueprint, current_app, request, render_template, make_response, jsonify, send_from_directory
from flask import session, abort
import jwt
import application.models.servers as serverModel
import application.models.users as userModel
from application.marshmallowSchemas import userSchema, serversSchema
from application.DBModels import User, db, Server
import os.path

from application.models.auth import create_access_token, get_email_from_token


def token_required(f):
    @wraps(f)
    def _verify(*args, **kwargs):
        auth_headers = request.headers.get('Authorization', '').split()

        invalid_msg = {
            'message': 'Invalid token. Registeration and / or authentication required',
            'authenticated': False
        }
        expired_msg = {
            'message': 'Expired token. Reauthentication required.',
            'authenticated': False
        }

        if len(auth_headers) != 2:
            return jsonify(invalid_msg), 401

        token_type, token_value = auth_headers
        if token_type.lower() == 'bearer':
            try:
                user = get_current_user(token_value, current_app)
                if not user:
                    abort(401)
                return f(user, *args, **kwargs)
            except jwt.ExpiredSignatureError:
                return jsonify(expired_msg), 401 # 401 is Unauthorized HTTP status code
            except (jwt.InvalidTokenError) as e:
                return jsonify(invalid_msg), 401

        elif token_type.lower() == 'apikey':
            user = get_current_user_api(token_value)
            if not user:
                abort(401)
            return f(user, *args, **kwargs)

    return _verify

def get_current_user(token, app):
    email = get_email_from_token(token, app)
    user = userModel.getByEmail(email)
    return user

def get_current_user_api(token):
    user = User.query.filter_by(apikey=token).first()
    return user


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
