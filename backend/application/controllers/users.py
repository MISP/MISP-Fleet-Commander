from flask import Blueprint, abort, request, render_template, make_response, jsonify
# from flask import current_app as app
from datetime import datetime as dt
from application.DBModels import db, User
from application.controllers.instance import token_required, admin_required, issue_access_token, MIN_PASSWORD_LENGTH
from application.marshmallowSchemas import userSchema, usersSchema
import application.models.users as userModel

BPuser = Blueprint('user', __name__)


def resolveUserId(loggedUser, user_id):
    """`me` or a numeric user ID. Users can only target themselves unless they are administrators"""
    if user_id == 'me':
        return loggedUser.id
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        abort(400)
    if user_id != loggedUser.id and not loggedUser.is_admin:
        abort(403, description='Administrator role required')
    return user_id


@BPuser.route('/users/view/<user_id>', methods=['GET'])
@token_required
def view(loggedUser, user_id):
    user = userModel.get(resolveUserId(loggedUser, user_id))
    if user is None:
        abort(404)
    return userSchema.dump(user)


@BPuser.route('/users/index', methods=['GET'])
@admin_required
def index(loggedUser):
    users = userModel.index()
    return usersSchema.dump(users)


@BPuser.route('/users/get/<int:user_id>', methods=['GET'])
@admin_required
def get(loggedUser, user_id):
    user = userModel.get(user_id)
    if user is not None:
        return userSchema.dump(user)
    else:
        return jsonify({})


@BPuser.route('/users/add', methods=['POST', 'PUT'])
@admin_required
def add(loggedUser):
    newUser = userModel.add(request.json)
    if newUser is not None:
        return userSchema.dump(newUser)
    else:
        return jsonify([])


@BPuser.route('/users/edit', methods=['POST'])
@token_required
def edit(loggedUser):
    userData = dict(request.json or {})
    userData['id'] = resolveUserId(loggedUser, userData.get('id', 'me'))
    if 'is_admin' in userData:
        # Only administrators change roles, and never their own: an instance can't lose its last administrator this way
        if not loggedUser.is_admin or userData['id'] == loggedUser.id:
            userData.pop('is_admin')
    updatedUser = userModel.edit(userData)
    if updatedUser is not None:
        return userSchema.dump(updatedUser)
    else:
        return jsonify([])


@BPuser.route('/users/delete/<int:user_id>', methods=['DELETE', 'POST'])
@admin_required
def delete(loggedUser, user_id):
    """Delete a user"""
    if user_id == loggedUser.id:
        return jsonify({'message': 'You cannot delete your own account'}), 400
    userToDelete = userModel.delete(user_id)
    if userToDelete:
        return jsonify([user_id])
    else:
        return jsonify({})


@BPuser.route('/users/change-password', methods=['POST'])
@token_required
def changePassword(loggedUser):
    """Users change their own password, proving they know the current one. Returns a fresh login token."""
    payload = request.get_json(silent=True) or {}
    currentPassword, newPassword = payload.get('current_password') or '', payload.get('new_password') or ''
    if not loggedUser.verify_password(currentPassword):
        return jsonify({'message': 'The current password is incorrect', 'field': 'current_password'}), 400
    if len(newPassword) < MIN_PASSWORD_LENGTH:
        return jsonify({'message': f'The new password must be at least {MIN_PASSWORD_LENGTH} characters long',
                        'field': 'new_password'}), 400
    if newPassword == currentPassword:
        return jsonify({'message': 'The new password must be different from the current one', 'field': 'new_password'}), 400
    loggedUser.password = newPassword
    loggedUser.must_change_password = False
    db.session.commit()
    return jsonify(issue_access_token(loggedUser))


@BPuser.route('/users/genAPIKey/<user_id>', methods=['POST'])
@token_required
def createAPIKey(loggedUser, user_id):
    """Generate a new API key. This response is the only place the key is ever shown"""
    token = userModel.createAPIKey(resolveUserId(loggedUser, user_id))
    return jsonify({'token': token})
