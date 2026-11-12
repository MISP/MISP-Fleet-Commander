from flask import Blueprint, jsonify, request
# from flask import current_app as app
from application.controllers.instance import token_required
import application.models.servers as serverModel


BPserverManagement = Blueprint('serverManagement', __name__)


def runOperation(user, server_id, operation, title, failureMessage, user_id=None, payload=None):
    """Run a user administration operation on one MISP server, recorded as a one-server job. Answers MISP's
    result, or `{"error": …}`"""
    from application.controllers.websocket import socketEmitter
    import application.models.jobRunner as jobRunner
    server = serverModel.getForUser(user, server_id)
    if server is None:
        return jsonify({'error': failureMessage})
    params = {'operation': operation}
    if user_id is not None:
        params['user_id'] = user_id
    if payload is not None:
        params['payload'] = payload
    unit = jobRunner.runInline(user, 'server_management', server, params, title=f'{title} on {server.name}',
                               emitter=socketEmitter)
    if not unit.ok:
        return jsonify({'error': unit.summary or failureMessage})
    return jsonify(unit.response)


@BPserverManagement.route('/server-management/user/add-options/<int:server_id>', methods=['GET'])
@token_required
def addUserOptions(user, server_id):
    """The organisations and roles of the MISP instance, to choose from when adding a user"""
    import application.models.serverManagement as serverManagementModel
    server = serverModel.getForUser(user, server_id)
    if server is None:
        return jsonify({'message': 'Unknown server'}), 404
    try:
        return jsonify(serverManagementModel.addUserOptions(server))
    except serverManagementModel.MISPListError as e:
        return jsonify({'message': f'Could not list the organisations and roles of {server.name}: {e}'}), 502


@BPserverManagement.route('/server-management/user/add/<int:server_id>', methods=['POST'])
@token_required
def addUser(user, server_id):
    """Create a user on the MISP instance"""
    payload = request.json or {}
    email = payload.get('email') if isinstance(payload, dict) else None
    return runOperation(user, server_id, 'add_user', f'Add user {email}' if email else 'Add user',
                        'Could not create user.', payload=payload)


@BPserverManagement.route('/server-management/user/set-password/<int:server_id>/<int:user_id>', methods=['POST'])
@token_required
def setPassword(user, server_id, user_id):
    """Set the password of a user on the MISP instance"""
    return runOperation(user, server_id, 'set_password', f'Set the password of user #{user_id}',
                        'Could not set password for user.', user_id=user_id, payload=request.json or {})


@BPserverManagement.route('/server-management/user/reset-password/<int:server_id>/<int:user_id>', methods=['POST'])
@token_required
def resetPassword(user, server_id, user_id):
    """Reset password for a user on the MISP instance"""
    return runOperation(user, server_id, 'reset_password', f'Reset the password of user #{user_id}',
                        'Could not reset password user.', user_id=user_id)


@BPserverManagement.route('/server-management/user/gen-authkey/<int:server_id>/<int:user_id>', methods=['POST'])
@token_required
def genAuthkey(user, server_id, user_id):
    """Generate an authkey for a user on the MISP instance"""
    return runOperation(user, server_id, 'gen_authkey', f'Generate an authkey for user #{user_id}',
                        'Could not generate authkey for user.', user_id=user_id)


@BPserverManagement.route('/server-management/user/disable/<int:server_id>/<int:user_id>', methods=['POST'])
@token_required
def disable(user, server_id, user_id):
    """Disable a user on the MISP instance"""
    return runOperation(user, server_id, 'disable', f'Disable user #{user_id}', 'Could not disable user.',
                        user_id=user_id)


@BPserverManagement.route('/server-management/user/enable/<int:server_id>/<int:user_id>', methods=['POST'])
@token_required
def enable(user, server_id, user_id):
    """Enable a user on the MISP instance"""
    return runOperation(user, server_id, 'enable', f'Enable user #{user_id}', 'Could not enable user.',
                        user_id=user_id)
