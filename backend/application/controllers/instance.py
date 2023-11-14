
from functools import wraps
import pathlib
from flask import Blueprint, current_app, request, render_template, make_response, jsonify, send_from_directory
from flask import session, abort
import jwt
import application.models.servers as serverModel
from application.marshmallowSchemas import userSchema, serversSchema
from application.DBModels import User, db, Server
import os.path

from application.models.auth import create_access_token, get_current_user


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

        try:
            token = auth_headers[1]
            user = get_current_user(token, current_app)
            if not user:
                raise RuntimeError('User not found')
            return f(user, *args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify(expired_msg), 401 # 401 is Unauthorized HTTP status code
        except (jwt.InvalidTokenError) as e:
            return jsonify(invalid_msg), 401

    return _verify


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

