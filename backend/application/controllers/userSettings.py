from flask import Blueprint, abort, request, render_template, make_response, jsonify
# from flask import current_app as app
from datetime import datetime as dt
from application.DBModels import UserSettings, db, User
from application.controllers.instance import token_required
from application.marshmallowSchemas import userSettingSchema, userSettingsSchema, userSchema
import application.models.users as userModel
import application.models.userSettings as userSettingsModel

BPuserSetting = Blueprint('userSettings', __name__)


def ownedSetting(loggedUser, id):
    """A setting of the logged user. Administrators can reach the settings of every user"""
    userSetting = userSettingsModel.get(id)
    if userSetting is None or (userSetting.user_id != loggedUser.id and not loggedUser.is_admin):
        abort(404)
    return userSetting


def targetUserId(loggedUser, user_id):
    """Users manage their own settings; administrators manage the settings of every user"""
    if user_id != loggedUser.id and not loggedUser.is_admin:
        abort(403, description='Administrator role required')
    return user_id


@BPuserSetting.route('/user-settings/view/<int:id>', methods=['GET'])
@token_required
def view(loggedUser, id):
    return userSettingSchema.dump(ownedSetting(loggedUser, id))


@BPuserSetting.route('/user-settings/get-for-user/<int:user_id>/<string:setting_name>', methods=['GET'])
@token_required
def getForUser(loggedUser, user_id, setting_name):
    userSetting = userSettingsModel.getForUser(targetUserId(loggedUser, user_id), setting_name)
    return userSettingSchema.dump(userSetting)


@BPuserSetting.route('/user-settings/edit-for-user/<int:user_id>', methods=['POST', 'PUT'])
@token_required
def editForUser(loggedUser, user_id):
    user_id = targetUserId(loggedUser, user_id)
    if request.json is not None:
        userSetting = userSettingsModel.editForUser(user_id, request.json)
        return userSettingSchema.dump(userSetting)
    return jsonify([])


@BPuserSetting.route('/user-settings/index', methods=['GET'])
@token_required
def index(loggedUser):
    """Settings of the logged user"""
    userSettings = userSettingsModel.indexForUser(loggedUser.id)
    return userSettingsSchema.dump(userSettings)


@BPuserSetting.route('/user-settings/add', methods=['POST', 'PUT'])
@token_required
def add(loggedUser):
    """Add a setting for the logged user"""
    newUserSettings = userSettingsModel.add(loggedUser.id, request.json)
    if newUserSettings is not None:
        return userSettingSchema.dump(newUserSettings)
    else:
        return jsonify([])


@BPuserSetting.route('/user-settings/edit', methods=['POST'])
@token_required
def edit(loggedUser):
    """Edit a setting by its ID: `{"id": ..., "value": ...}`"""
    userSetting = ownedSetting(loggedUser, (request.json or {}).get('id'))
    updatedUserSettings = userSettingsModel.edit(userSetting.id, request.json)
    if updatedUserSettings is not None:
        return userSettingSchema.dump(updatedUserSettings)
    else:
        return jsonify([])


@BPuserSetting.route('/user-settings/delete/<int:id>', methods=['DELETE', 'POST'])
@token_required
def delete(loggedUser, id):
    """Delete a user setting"""
    userSettingToDelete = userSettingsModel.delete(ownedSetting(loggedUser, id).id)
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
