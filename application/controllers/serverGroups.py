from flask import Blueprint, request, render_template, make_response, jsonify
# from flask import current_app as app
from datetime import datetime as dt
import time
from application.DBModels import db, User, Server, ServerGroup


BPserverGroup = Blueprint('serverGroup', __name__)


@BPserverGroup.route('/serverGroups/index', methods=['GET'])
def index():
    sgs = ServerGroup.query.all()
    return jsonify([sg.to_dict() for sg in sgs])


@BPserverGroup.route('/serverGroups/get/<int:group_id>', methods=['GET'])
def get(group_id):
    group = ServerGroup.query.get(group_id)
    if group is not None:
        return jsonify(group.to_dict())
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
    return jsonify(group.to_dict())


@BPserverGroup.route('/serverGroups/edit', methods=['POST'])
def edit():
    """Create a user."""
    email = request.args.get('email')
    if email:
        new_user = User(email=email,
                        created=dt.now(),
                        password="Password1234")
        db.session.add(new_user)  # Adds new User record to database
        db.session.commit()  # Commits all changes
    return make_response(f"{new_user} successfully created!")


@BPserverGroup.route('/serverGroups/delete', methods=['POST'])
def delete():
    """Create a user."""
    email = request.args.get('email')
    if email:
        new_user = User(email=email,
                        created=dt.now(),
                        password="Password1234")
        db.session.add(new_user)  # Adds new User record to database
        db.session.commit()  # Commits all changes
    return make_response(f"{new_user} successfully created!")

@BPserverGroup.route('/serverGroups/getFromServerId/<int:server_id>', methods=['GET'])
def getFromServerId(server_id):
    server = Server.query.get(server_id)
    if server is not None:
        group = ServerGroup.query.get(server.server_group_id)
        return jsonify(group.to_dict())
    else:
        return jsonify({})

