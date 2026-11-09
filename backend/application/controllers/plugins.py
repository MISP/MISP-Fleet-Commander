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


def runPluginInline(user, server_id, plugin_id, quick):
    """Run a plugin's action on one server, recorded as a one-server job. Answers in the plugin response format"""
    import application
    from application.controllers.websocket import socketEmitter
    import application.models.jobRunner as jobRunner
    server = serverModel.getForUser(user, server_id)
    if server is None:
        return jsonify([])
    plugin = pluginsModel.getPluginFromID(application.loadedPlugins or [], plugin_id)
    if plugin is None:
        return jsonify({'status': 'fail', 'data': {}, 'error': [f'Unknown plugin `{plugin_id}`']}), 404
    if quick:
        kind, label = 'plugin_quick_action', plugin['quickActionMeta']['quickActionName']
    else:
        kind, label = 'plugin_action', plugin['name']
    unit = jobRunner.runInline(user, kind, server, {'plugin_id': plugin_id, 'data': request.json},
                               title=f'{label} on {server.name}', emitter=socketEmitter)
    if isinstance(unit.response, dict):
        return jsonify(unit.response)
    return jsonify({'status': 'fail', 'data': {}, 'error': [unit.summary]})


@BPplugins.route('/plugins/doAction/<int:server_id>/<plugin_id>', methods=['POST'])
@token_required
def doAction(user, server_id, plugin_id):
    return runPluginInline(user, server_id, plugin_id, quick=False)


@BPplugins.route('/plugins/doQuickAction/<int:server_id>/<plugin_id>', methods=['POST'])
@token_required
def doQuickAction(user, server_id, plugin_id):
    return runPluginInline(user, server_id, plugin_id, quick=True)


@BPplugins.route('/plugins/notifications/<int:server_id>', methods=['GET'])
@token_required
def notifications(user, server_id):
    server = serverModel.getForUser(user, server_id)
    if server:
        allNotifications = pluginsModel.getAllNotifications(loadedPlugins, server)
        return allNotifications
    else:
        return jsonify([])
