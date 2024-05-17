from flask import Blueprint, abort, request, render_template, make_response, jsonify
# from flask import current_app as app
from datetime import datetime as dt
from application.DBModels import UserSettings, db, User
from application.controllers.instance import token_required
from application.marshmallowSchemas import userSettingSchema, userSettingsSchema, userSchema
import application.models.users as userModel
import application.models.userSettings as userSettingsModel

BPuserSetting = Blueprint('userSettings', __name__)


@BPuserSetting.route('/user-settings/view/<int:id>', methods=['GET'])
@token_required
def view(loggedUser, id):
    userSetting = userSettingsModel.get(id)
    return userSettingSchema.dump(userSetting)


@BPuserSetting.route('/user-settings/get-for-user/<int:user_id>/<string:setting_name>', methods=['GET'])
@token_required
def getForUser(loggedUser, user_id, setting_name):
    if user_id == 'me':
        user_id = loggedUser.id
    else:
        try:
            user_id = int(user_id)
        except ValueError:
            abort(400)
            
    userSetting = userSettingsModel.getForUser(user_id, setting_name)
    return userSettingSchema.dump(userSetting)


@BPuserSetting.route('/user-settings/edit-for-user/<int:user_id>', methods=['POST', 'PUT'])
@token_required
def editForUser(loggedUser, user_id):
    if user_id == 'me':
        user_id = loggedUser.id
    else:
        try:
            user_id = int(user_id)
        except ValueError:
            abort(400)

    if request.json is not None:
        userSetting = userSettingsModel.editForUser(user_id, request.json)
        return userSettingSchema.dump(userSetting)
    return jsonify([])


@BPuserSetting.route('/user-settings/index', methods=['GET'])
@token_required
def index(loggedUser):
    users = userSettingsModel.index()
    return userSettingsSchema.dump(users)


@BPuserSetting.route('/user-settings/add', methods=['POST', 'PUT'])
@token_required
def add(loggedUser):
    newUserSettings = userSettingsModel.add(request.json)
    if newUserSettings is not None:
        return userSettingSchema.dump(newUserSettings)
    else:
        return jsonify([])


@BPuserSetting.route('/user-settings/edit', methods=['POST'])
@token_required
def edit(loggedUser):
    updatedUserSettings = userSettingsModel.edit(request.json)
    if updatedUserSettings is not None:
        return userSettingSchema.dump(updatedUserSettings)
    else:
        return jsonify([])


@BPuserSetting.route('/user-settings/delete/<int:id>', methods=['DELETE', 'POST'])
@token_required
def delete(loggedUser, id):
    """Delete a user"""
    userSettingToDelete = userSettingsModel.delete(id)
    if userSettingToDelete:
        return jsonify([id])
    else:
        return jsonify({})


@BPuserSetting.route('/user-settings/get-setting-config', methods=['GET'])
@token_required
def getSettingConfig(loggedUser):
    """Get the configuration of all user settings"""
    return jsonify(userSettingsModel.getSettingConfig())


@BPuserSetting.route('/user-settings/toggle-plugin/<pluginName>', methods=['POST', 'PUT'])
@token_required
def togglePlugin(loggedUser, pluginName):
    """Enable the given plugin for the logged user"""
    enabledPlugins = userSettingsModel.togglePlugin(loggedUser.id, pluginName)
    return jsonify(enabledPlugins)
