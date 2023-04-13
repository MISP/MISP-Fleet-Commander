from flask import Blueprint, request, jsonify
# from flask import current_app as app
from application.DBModels import Server
from application import loadedPlugins
from application.marshmallowSchemas import pluginsSchema
import application.models.servers as serverModel
import application.models.plugins as pluginsModel


BPplugins = Blueprint('plugins', __name__)


@BPplugins.route('/plugins/index', methods=['GET'])
def index():
    plugins = loadedPlugins
    return pluginsSchema.dump(plugins)

@BPplugins.route('/plugins/indexValues/<int:group_id>', methods=['GET'])
def indexValues(group_id=None):
    servers = serverModel.index(group_id)
    if servers:
        allIndexValues = pluginsModel.getAllIndexValues(loadedPlugins, servers)
        return allIndexValues
    else:
        return jsonify([])

@BPplugins.route('/plugins/viewValues/<int:server_id>', methods=['GET'])
def viewValues(server_id):
    server = Server.query.get(server_id)
    if server:
        allViewValues = pluginsModel.getAllViewValues(loadedPlugins, server)
        return allViewValues
    else:
        return jsonify([])

@BPplugins.route('/plugins/doAction/<int:server_id>/<plugin_id>', methods=['POST'])
def doAction(server_id, plugin_id):
    server = Server.query.get(server_id)
    if server:
        plugin = pluginsModel.getPluginFromID(loadedPlugins, plugin_id)
        actionData = request.json
        actionResult = pluginsModel.doAction(server, plugin, actionData)
        return actionResult
    else:
        return jsonify([])

@BPplugins.route('/plugins/notifications/<int:server_id>', methods=['GET'])
def notifications(server_id):
    server = Server.query.get(server_id)
    if server:
        allNotifications = pluginsModel.getAllNotifications(loadedPlugins, server)
        return allNotifications
    else:
        return jsonify([])
