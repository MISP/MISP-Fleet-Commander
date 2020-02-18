from flask import Blueprint, request, render_template, make_response, jsonify
# from flask import current_app as app
from datetime import datetime as dt
from application.models import db, User, Server


BPserver = Blueprint('server', __name__)


@BPserver.route('/servers/index', methods=['GET'])
def index():
    servers = Server.query.all()
    return jsonify(User.serialize_list(servers))


@BPserver.route('/servers/add', methods=['POST'])
def add():
    # server = Server(name=,
    #                 url=,
    #                 authkey=
    #                 user_id=1)
    # db.session.add(server)
    # db.session.commit()
    # return jsonify(server.serialize())
    print(request.form)
    return 1