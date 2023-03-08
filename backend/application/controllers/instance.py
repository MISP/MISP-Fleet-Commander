from flask import Blueprint, request, render_template, make_response, jsonify, send_from_directory
import application.models.servers as serverModel
from application.DBModels import db, Server
import os.path


BPinstance = Blueprint('instance', __name__)


@BPinstance.route('/', defaults={'path': ''})
@BPinstance.route('/<string:path>')
@BPinstance.route('/<path:path>')
def static_proxy(path):
    if os.path.isfile('./dist/' + path):
        # If request is made for a file by vue.js for example main.js
        # condition will be true, file will be served from the public directory
        return send_from_directory('../dist', path)
    else:
        # Otherwise index.html will be served,
        # vue.js router will handle the rest
        return send_from_directory('../dist', "index.html")


@BPinstance.route('/instance/searchAll/<searchtext>', methods=['GET'])
def index(searchtext):
    servers = serverModel.searchAll(searchtext)
    return jsonify([server.to_dict() for server in servers])
