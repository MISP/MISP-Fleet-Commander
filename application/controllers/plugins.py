from collections import defaultdict
from flask import Blueprint, request, render_template, make_response, jsonify
# from flask import current_app as app
from datetime import datetime as dt
from application.DBModels import db, Server
from application import loadedPlugins
import application.models.servers as serverModel
import application.models.plugins as pluginsModel


BPplugins = Blueprint('plugins', __name__)
# AM = AdministrationManager()


@BPplugins.route('/plugins/index', methods=['GET'])
def index():
    ignoredKeys = ['instance']
    return jsonify([
        {
            k: v for k, v in plugin.items() if k not in ignoredKeys
        } for plugin in loadedPlugins
    ])

@BPplugins.route('/plugins/indexValues/<int:group_id>', methods=['GET'])
def indexValues(group_id=None):
    servers = serverModel.index(group_id)
    if servers:
        allIndexValues = pluginsModel.getAllIndexValues(loadedPlugins, servers)
        response = {
            serverID: {
                pluginID: indexValue.to_dict() for pluginID, indexValue in pluginValues.items()
            } for serverID, pluginValues in allIndexValues.items()
        }
        return jsonify(response)
    else:
        return jsonify([])

@BPplugins.route('/plugins/viewValues/<int:server_id>', methods=['GET'])
def viewValues(server_id):
    server = Server.query.get(server_id)
    if server:
        allViewValues = pluginsModel.getAllViewValues(loadedPlugins, server)
        response = {
            pluginID: viewValue.to_dict() for pluginID, viewValue in allViewValues.items()
        }
        return jsonify(response)
    else:
        return jsonify([])


# @BPplugins.route('/plugins/administration/view/<str:pluginName>/<int:server_id>', methods=['GET'])
# def add(pluginName, server_id):
#     server = Server.query.get(server_id)
#     if server is not None:
#         helper = AM.getHelper(pluginName)
#         results = helper.getView(server, request.json)
#         return jsonify(results)
#     else:
#         return jsonify({'error': 'Unkown server'})

# @BPplugins.route('/plugins/administration/exec/<str:pluginName>/<int:server_id>', methods=['GET'])
# def add(pluginName, server_id):
#     server = Server.query.get(server_id)
#     if server is not None:
#         helper = AM.getHelper(pluginName)
#         results = helper.execPlugin(server, request.json)
#         return jsonify(results)
#     else:
#         return jsonify({'error': 'Unkown server'})





# @BPplugins.route('/plugins/index', methods=['GET'])
# def index():
#     helpers = AM.getHelperByName()
#     return jsonify([helper.to_dict() for helper in helpers])


# @BPplugins.route('/plugins/administration/view/<str:pluginName>/<int:server_id>', methods=['GET'])
# def add(pluginName, server_id):
#     server = Server.query.get(server_id)
#     if server is not None:
#         helper = AM.getHelper(pluginName)
#         results = helper.getView(server, request.json)
#         return jsonify(results)
#     else:
#         return jsonify({'error': 'Unkown server'})

# @BPplugins.route('/plugins/administration/exec/<str:pluginName>/<int:server_id>', methods=['GET'])
# def add(pluginName, server_id):
#     server = Server.query.get(server_id)
#     if server is not None:
#         helper = AM.getHelper(pluginName)
#         results = helper.execPlugin(server, request.json)
#         return jsonify(results)
#     else:
#         return jsonify({'error': 'Unkown server'})
