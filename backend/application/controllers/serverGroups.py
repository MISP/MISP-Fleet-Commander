from flask import Blueprint, request, jsonify
# from flask import current_app as app
from datetime import datetime as dt
import time
from application.DBModels import db, User, Server, ServerGroup
from application.marshmallowSchemas import serverGroupSchema, serverGroupsSchema
from application.controllers.instance import token_required
import application.models.serverGroups as serverGroupModel
import application.models.servers as serverModel


BPserverGroup = Blueprint('serverGroup', __name__)

@BPserverGroup.route('/serverGroups/index', methods=['GET'])
@token_required
def index(user):
    groups = serverGroupModel.indexForUser(user)
    return serverGroupsSchema.dump(groups)


@BPserverGroup.route('/serverGroups/get/<int:group_id>', methods=['GET'])
@token_required
def get(user, group_id):
    group = serverGroupModel.getForUser(user, group_id)
    if group is not None:
        return serverGroupSchema.dump(group)
    else:
        return jsonify({})


@BPserverGroup.route('/serverGroups/add', methods=['POST'])
@token_required
def add(user):
    group = ServerGroup(name=request.json.get('name'),
                    description=request.json.get('description'),
                    timestamp=int(time.time()),
                    user_id=user.id)
    db.session.add(group)
    db.session.commit()
    return serverGroupSchema.dump(group)


@BPserverGroup.route('/serverGroups/delete/<int:group_id>', methods=['DELETE', 'POST'])
@token_required
def delete(user, group_id):
    """Delete a group and it's associated servers"""
    group = serverGroupModel.getForUser(user, group_id)
    if group is not None:
        db.session.delete(group)
        db.session.commit()
        return jsonify([group_id])
    else:
        return jsonify({})

@BPserverGroup.route('/serverGroups/getFromServerId/<int:server_id>', methods=['GET'])
@token_required
def getFromServerId(user, server_id):
    server = serverModel.getForUser(user, server_id)
    if server is not None:
        group = serverGroupModel.getForUser(user, server.server_group_id)
        return serverGroupSchema.dump(group)
    else:
        return jsonify({})

