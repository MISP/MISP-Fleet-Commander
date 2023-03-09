from flask import Blueprint, request, jsonify
# from flask import current_app as app
from datetime import datetime as dt
import time
from application.DBModels import db, User, Server, ServerGroup
from application.marshmallowSchemas import serverGroupSchema, serverGroupsSchema


BPserverGroup = Blueprint('serverGroup', __name__)


@BPserverGroup.route('/serverGroups/index', methods=['GET'])
def index():
    sgs = ServerGroup.query.all()
    return serverGroupsSchema.dump(sgs)


@BPserverGroup.route('/serverGroups/get/<int:group_id>', methods=['GET'])
def get(group_id):
    group = ServerGroup.query.get(group_id)
    if group is not None:
        return serverGroupSchema(group)
    else:
        return jsonify({})


@BPserverGroup.route('/serverGroups/add', methods=['POST'])
def add():
    group = ServerGroup(name=request.json.get('name'),
                    description=request.json.get('description'),
                    timestamp=int(time.time()),
                    user_id=1)
    db.session.add(group)
    db.session.commit()
    return serverGroupSchema(group)


@BPserverGroup.route('/serverGroups/delete/<int:group_id>', methods=['DELETE', 'POST'])
def delete(group_id):
    """Delete a group and it's associated servers"""
    group = ServerGroup.query.get(group_id)
    if group is not None:
        db.session.delete(group)
        db.session.commit()
        return jsonify([group_id])
    else:
        return jsonify({})

@BPserverGroup.route('/serverGroups/getFromServerId/<int:server_id>', methods=['GET'])
def getFromServerId(server_id):
    server = Server.query.get(server_id)
    if server is not None:
        group = ServerGroup.query.get(server.server_group_id)
        return serverGroupSchema(group)
    else:
        return jsonify({})

