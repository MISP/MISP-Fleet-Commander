from flask import Blueprint, request, render_template, make_response, jsonify
# from flask import current_app as app
from datetime import datetime as dt
from application.models import db, User, Server
from application.controllers.utils import mispGetRequest, mispPostRequest

BPserver = Blueprint('server', __name__)


@BPserver.route('/servers/index', methods=['GET'])
def index():
    servers = Server.query.all()
    return jsonify(User.serialize_list(servers))


@BPserver.route('/servers/add', methods=['POST'])
def add():
    server = Server(name=request.json.get('name'),
                    url=request.json.get('url'),
                    skip_ssl=request.json.get('skip_ssl', False),
                    authkey=request.json.get('authkey'),
                    user_id=1)
    db.session.add(server)
    if request.json['recursive_add']:
        # recursively add servers
        pass
    db.session.commit()
    return jsonify(server.serialize())


@BPserver.route('/servers/edit', methods=['POST'])
def edit():
    saveFields = ['name', 'url', 'skip_ssl', 'authkey']
    server = Server.query.get(request.json['id'])
    if server is not None:
        for field, value in request.json.items():
            if field in saveFields:
                setattr(server, field, value)
    if request.json['recursive_add']:
        # recursively add servers
        pass
    db.session.commit()
    return jsonify(server.serialize())


@BPserver.route('/servers/delete', methods=['POST'])
def delete():
    server = Server.query.get(request.json['id'])
    if server is not None:
        db.session.delete(server)
        db.session.commit()
        return jsonify(server.serialize())
    else:
        return jsonify({})

@BPserver.route('/servers/testConnection/<int:server_id>', methods=['GET'])
def ping_server(server_id):
    server = Server.query.get(server_id)
    if server is not None:
        testConnection = mispGetRequest(server, '/servers/getVersion')
        return jsonify(testConnection)
    else:
        return jsonify({})

@BPserver.route('/servers/queryDiagnostic/<int:server_id>', methods=['POST'])
def queryDiagnostic(server_id):
    server = Server.query.get(server_id)
    if server is not None:
        diagnostic = mispGetRequest(server, '/servers/serverSettings/diagnostics/light:1')
        return jsonify(diagnostic)
    else:
        return jsonify({})