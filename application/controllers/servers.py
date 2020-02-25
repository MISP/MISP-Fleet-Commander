from flask import Blueprint, request, render_template, make_response, jsonify
# from flask import current_app as app
from datetime import datetime as dt
import time
from application.models import db, User, Server, ServerQuery
from application.controllers.utils import mispGetRequest, mispPostRequest

BPserver = Blueprint('server', __name__)


@BPserver.route('/servers/index', methods=['GET'])
def index():
    servers = Server.query.all()
    return jsonify(Server.serialize_list(servers))


@BPserver.route('/servers/add', methods=['POST'])
def add():
    server = Server(name=request.json.get('name'),
                    url=request.json.get('url'),
                    skip_ssl=request.json.get('skip_ssl', False),
                    authkey=request.json.get('authkey'),
                    user_id=1)
    db.session.add(server)
    if request.json.get('recursive_add', False):
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
    if request.json.get('recursive_add', False):
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
        testConnection['timestamp'] = int(time.time())
        return jsonify(testConnection)
    else:
        return jsonify({})

@BPserver.route('/servers/queryDiagnostic/<int:server_id>', methods=['GET'])
def queryDiagnostic(server_id, no_cache=False):
    server = Server.query.get(server_id)
    if server is not None:
        if no_cache:
            server_query = mispGetRequest(server, '/servers/serverSettings/diagnostics/light:1')
            server_query_db = saveDiagnostic(server_id, server_query)
        else:
            server_query_db = ServerQuery.query.filter_by(server_id=server_id).first()
            if server_query_db is None: # No query associated to the server
                server_query = mispGetRequest(server, '/servers/serverSettings/diagnostics/light:1')
                server_query_db = saveDiagnostic(server_id, server_query)
        print(server_query_db)
        return jsonify(server_query_db.serialize())
    else:
        return jsonify({'error': 'Unkown server'})

# ===========
def saveDiagnostic(server_id, queryResult):
    now = int(time.time())
    server_query = ServerQuery(server_id=server_id,
                    timestamp=now,
                    query_result=queryResult)
    db.session.add(server_query)
    db.session.commit()
    return server_query