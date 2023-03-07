from flask import Blueprint, request, render_template, make_response, jsonify
import application.models.servers as serverModel
from application.DBModels import db, Server


BPinstance = Blueprint('instance', __name__)


@BPinstance.route('/instance/searchAll/<searchtext>', methods=['GET'])
def index(searchtext):
    servers = serverModel.searchAll(searchtext)
    return jsonify([server.to_dict() for server in servers])
