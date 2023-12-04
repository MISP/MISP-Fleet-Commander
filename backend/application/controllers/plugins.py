from flask import Blueprint, request, jsonify
# from flask import current_app as app
from application.DBModels import Server
from application import loadedPlugins
from application.marshmallowSchemas import pluginsSchema
import application.models.servers as serverModel
import application.models.plugins as pluginsModel
from application.controllers.instance import token_required


BPplugins = Blueprint('plugins', __name__)


@BPplugins.route('/plugins/index', methods=['GET'])
@token_required
def index(user):
    plugins = loadedPlugins
    return pluginsSchema.dump(plugins)

@BPplugins.route('/plugins/indexValues/<int:fleet_id>', methods=['GET'])
@token_required
def indexValues(user, fleet_id=None):
    servers = serverModel.indexForUser(user, fleet_id)
    if servers:
        allIndexValues = pluginsModel.getAllIndexValues(loadedPlugins, servers)
        return allIndexValues
    else:
        return jsonify([])

@BPplugins.route('/plugins/viewValues/<int:server_id>', methods=['GET'])
@token_required
def viewValues(user, server_id):
    server = serverModel.getForUser(user, server_id)
    if server:
        allViewValues = pluginsModel.getAllViewValues(loadedPlugins, server)
        return allViewValues
    else:
        return jsonify([])

@BPplugins.route('/plugins/doAction/<int:server_id>/<plugin_id>', methods=['POST'])
@token_required
def doAction(user, server_id, plugin_id):
    server = serverModel.getForUser(user, server_id)
    if server:
        plugin = pluginsModel.getPluginFromID(loadedPlugins, plugin_id)
        actionData = request.json
        actionResult = pluginsModel.doAction(server, plugin, actionData)
        return actionResult
    else:
        return jsonify([])

@BPplugins.route('/plugins/notifications/<int:server_id>', methods=['GET'])
@token_required
def notifications(user, server_id):
    server = serverModel.getForUser(user, server_id)
    if server:
        allNotifications = pluginsModel.getAllNotifications(loadedPlugins, server)
        return allNotifications
    else:
        return jsonify([])
