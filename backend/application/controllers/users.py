from flask import Blueprint, abort, request, render_template, make_response, jsonify
# from flask import current_app as app
from datetime import datetime as dt
from application.DBModels import db, User
from application.controllers.instance import token_required
from application.marshmallowSchemas import userSchema, usersSchema
import application.models.users as userModel

BPuser = Blueprint('user', __name__)


@BPuser.route('/users/view/<user_id>', methods=['GET'])
@token_required
def view(loggedUser, user_id):
    if user_id == 'me':
        user_id = loggedUser.id
    else:
        try:
            user_id = int(user_id)
        except ValueError:
            abort(400)
            
    user = userModel.get(user_id)
    return userSchema.dump(user)


@BPuser.route('/users/index', methods=['GET'])
@token_required
def index(loggedUser):
    users = userModel.index()
    return usersSchema.dump(users)


@BPuser.route('/users/get/<int:user_id>', methods=['GET'])
@token_required
def get(loggedUser, user_id):
    user = userModel.get(user_id)
    if user is not None:
        return userSchema.dump(user)
    else:
        return jsonify({})


@BPuser.route('/users/add', methods=['POST', 'PUT'])
@token_required
def add(loggedUser):
    newUser = userModel.add(request.json)
    if newUser is not None:
        return userSchema.dump(newUser)
    else:
        return jsonify([])


@BPuser.route('/users/edit', methods=['POST'])
@token_required
def edit(loggedUser):
    updatedUser = userModel.edit(request.json)
    if updatedUser is not None:
        return userSchema.dump(updatedUser)
    else:
        return jsonify([])


@BPuser.route('/users/delete/<int:user_id>', methods=['DELETE', 'POST'])
@token_required
def delete(loggedUser, user_id):
    """Delete a user"""
    userToDelete = userModel.delete(user_id)
    if userToDelete:
        return jsonify([user_id])
    else:
        return jsonify({})


@BPuser.route('/users/genAPIKey/<int:user_id>', methods=['POST'])
@token_required
def createAPIKey(loggedUser, user_id):
    token = userModel.createAPIKey(user_id)
    return jsonify({'token': token})