from flask import Blueprint, request, render_template, make_response, jsonify
# from flask import current_app as app
from datetime import datetime as dt
from application.DBModels import db, Server
from application.plugins.server_administration.AdministrationManager import AdministrationManager


BPplugins = Blueprint('plugins', __name__)
AM = AdministrationManager()


@BPplugins.route('/plugins/index', methods=['GET'])
def index():
    helpers = AM.getHelperByName()
    return jsonify([helper.to_dict() for helper in helpers])


@BPplugins.route('/plugins/administration/view/<str:pluginName>/<int:server_id>', methods=['GET'])
def add(pluginName, server_id):
    server = Server.query.get(server_id)
    if server is not None:
        helper = AM.getHelper(pluginName)
        results = helper.getView(server, request.json)
        return jsonify(results)
    else:
        return jsonify({'error': 'Unkown server'})

@BPplugins.route('/plugins/administration/exec/<str:pluginName>/<int:server_id>', methods=['GET'])
def add(pluginName, server_id):
    server = Server.query.get(server_id)
    if server is not None:
        helper = AM.getHelper(pluginName)
        results = helper.execPlugin(server, request.json)
        return jsonify(results)
    else:
        return jsonify({'error': 'Unkown server'})
