from flask import Blueprint, jsonify, request
# from flask import current_app as app
from application.controllers.instance import token_required
import application.models.servers as serverModel
from application.models import serverManagement


BPserverManagement = Blueprint('serverManagement', __name__)

@BPserverManagement.route('/server-management/user/add/<int:server_id>', methods=['POST'])
@token_required
def addUser(user, server_id):
    """Create a user on the MISP instance"""
    server = serverModel.getForUser(user, server_id)
    if server is not None:
        result = serverManagement.addUser(server, request.json)
        if result is not None:
            return jsonify(result)
    return jsonify({'error': 'Could not create user.'})


@BPserverManagement.route('/server-management/user/set-password/<int:server_id>/<int:user_id>', methods=['POST'])
@token_required
def setPassword(user, server_id, user_id):
    """Set the password of a user on the MISP instance"""
    server = serverModel.getForUser(user, server_id)
    result = serverManagement.setPassword(server, user_id, request.json)
    if result is not None:
        if 'errors' in result:
            return jsonify({'error': result['message'] + ' - ' + ', '.join(result['errors']['password'])})
        else:
            return jsonify(result)
    return jsonify({'error': 'Could not set password for user.'})


@BPserverManagement.route('/server-management/user/reset-password/<int:server_id>/<int:user_id>', methods=['POST'])
@token_required
def resetPassword(user, server_id, user_id):
    """Reset password for a user on the MISP instance"""
    server = serverModel.getForUser(user, server_id)
    result = serverManagement.resetPassword(server, user_id)
    if result is not None:
        return jsonify(result)
    return jsonify({'error': 'Could not reset password user.'})


@BPserverManagement.route('/server-management/user/gen-authkey/<int:server_id>/<int:user_id>', methods=['POST'])
@token_required
def genAuthkey(user, server_id, user_id):
    """Generate an authkey for a user on the MISP instance"""
    server = serverModel.getForUser(user, server_id)
    result = serverManagement.genAuthkey(server, user_id)
    if result is not None:
        return jsonify(result)
    return jsonify({'error': 'Could not generate authkey for user.'})


@BPserverManagement.route('/server-management/user/disable/<int:server_id>/<int:user_id>', methods=['POST'])
@token_required
def disable(user, server_id, user_id):
    """Disable a user on the MISP instance"""
    server = serverModel.getForUser(user, server_id)
    if server is not None:
        result = serverManagement.disable(server, user_id)
        if result is not None:
            return jsonify(result)
    return jsonify({'error': 'Could not disable user.'})


@BPserverManagement.route('/server-management/user/enable/<int:server_id>/<int:user_id>', methods=['POST'])
@token_required
def enable(user, server_id, user_id):
    """Enable a user on the MISP instance"""
    server = serverModel.getForUser(user, server_id)
    if server is not None:
        result = serverManagement.enable(server, user_id)
        if result is not None:
            return jsonify(result)
    return jsonify({'error': 'Could not enable user.'})

