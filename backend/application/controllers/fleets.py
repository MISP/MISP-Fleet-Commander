from flask import Blueprint, request, jsonify
# from flask import current_app as app
from datetime import datetime as dt
import time
from application.DBModels import db, User, Server, Fleet
from application.marshmallowSchemas import fleetSchema, fleetsSchema
from application.controllers.instance import token_required
import application.models.fleets as fleetModel
import application.models.servers as serverModel


BPfleet = Blueprint('fleet', __name__)

@BPfleet.route('/fleets/index', methods=['GET'])
@token_required
def index(user):
    fleets = fleetModel.indexForUser(user)
    return fleetsSchema.dump(fleets)


@BPfleet.route('/fleets/get/<int:fleet_id>', methods=['GET'])
@token_required
def get(user, fleet_id):
    fleet = fleetModel.getForUser(user, fleet_id)
    if fleet is not None:
        return fleetSchema.dump(fleet)
    else:
        return jsonify({})


@BPfleet.route('/fleets/add', methods=['POST'])
@token_required
def add(user):
    fleet = Fleet(
        name=request.json.get("name"),
        description=request.json.get("description"),
        is_monitored=request.json.get("is_monitored"),
        timestamp=int(time.time()),
        user_id=user.id,
    )
    db.session.add(fleet)
    db.session.commit()
    return fleetSchema.dump(fleet)


@BPfleet.route("/fleets/edit/<int:fleet_id>", methods=["POST"])
@token_required
def edit(user, fleet_id):
    saveFields = ["name", "description", "is_monitored"]
    fleet = fleetModel.getForUser(user, fleet_id)
    if fleet is not None:
        for field, value in request.json.items():
            if field in saveFields:
                setattr(fleet, field, value)
    # fleet = Fleet(name=request.json.get('name'),
    #                 description=request.json.get('description'),
    #                 timestamp=int(time.time()),
    #                 user_id=user.id)
    db.session.commit()
    return fleetSchema.dump(fleet)


@BPfleet.route('/fleets/delete/<int:fleet_id>', methods=['DELETE', 'POST'])
@token_required
def delete(user, fleet_id):
    """Delete a fleet and it's associated servers"""
    fleet = fleetModel.getForUser(user, fleet_id)
    if fleet is not None:
        db.session.delete(fleet)
        db.session.commit()
        return jsonify([fleet_id])
    else:
        return jsonify({})

@BPfleet.route('/fleets/getFromServerId/<int:server_id>', methods=['GET'])
@token_required
def getFromServerId(user, server_id):
    server = serverModel.getForUser(user, server_id)
    if server is not None:
        fleet = fleetModel.getForUser(user, server.fleet_id)
        return fleetSchema.dump(fleet)
    else:
        return jsonify({})
