from flask import Blueprint, abort, request, jsonify
# from flask import current_app as app
from datetime import datetime as dt
import time
from application.DBModels import db, User, Server, Fleet
from application.marshmallowSchemas import fleetSchema, fleetsSchema
from application.controllers.instance import token_required
from application.controllers.jobs import jsonBody
import application.models.fleets as fleetModel
import application.models.usageWidgets as usageWidgets
import application.models.fleetMetrics as fleetMetricsModel
import application.models.metrics as metricModel
import application.models.metricSeries as metricSeriesModel
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
        is_watched=request.json.get("is_watched"),
        timestamp=int(time.time()),
        user_id=user.id,
    )
    db.session.add(fleet)
    db.session.commit()
    return fleetSchema.dump(fleet)


@BPfleet.route("/fleets/edit/<int:fleet_id>", methods=["POST"])
@token_required
def edit(user, fleet_id):
    saveFields = ["name", "description", "is_monitored", "is_watched"]
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


@BPfleet.route('/fleets/metrics/<int:fleet_id>', methods=['GET'])
@token_required
def fleetMetrics(user, fleet_id):
    """Usage metrics of the fleet over `range` (24h, 7d, 30d, 90d, 1y): its servers' figures summed per hour or day,
    and each server's own figures, optionally only for the `metrics` given (comma-separated keys)"""
    fleet = fleetModel.getForUser(user, fleet_id)
    if fleet is None:
        abort(404)
    try:
        rangeName, tier, keys = fleetMetricsModel.parseRequest(request.args.get('range'), request.args.get('metrics'))
    except metricSeriesModel.SeriesRequestError as e:
        return jsonify({'message': str(e)}), 400
    return jsonify(fleetMetricsModel.fleetSeries(fleet, rangeName, tier, keys, metricModel.monitoringSettings()))


# Widgets of the Usage tab

def widgetRefused(error: usageWidgets.JobError):
    body = {'message': error.message}
    if getattr(error, 'field', None):
        body['field'] = error.field
    return jsonify(body), error.status


@BPfleet.route('/fleets/<int:fleet_id>/widgets', methods=['GET'])
@token_required
def widgetIndex(user, fleet_id):
    """The saved queries followed on the fleet's Usage tab, in order, each with how the fleet's servers last
    answered it"""
    try:
        return jsonify(usageWidgets.listFor(user, fleet_id))
    except usageWidgets.JobError as e:
        return widgetRefused(e)


@BPfleet.route('/fleets/<int:fleet_id>/widgets/candidates', methods=['GET'])
@token_required
def widgetCandidates(user, fleet_id):
    """The user's SELECT and COUNT saved queries that run on at least one of the fleet's servers"""
    try:
        return jsonify(usageWidgets.candidates(user, fleet_id))
    except usageWidgets.JobError as e:
        return widgetRefused(e)


@BPfleet.route('/fleets/<int:fleet_id>/widgets', methods=['POST'])
@token_required
def widgetAdd(user, fleet_id):
    """Follow a saved query on the fleet's Usage tab: `{saved_query_id, display: total | servers}`. 400 with
    `field`, 409 when it is already there"""
    try:
        return jsonify(usageWidgets.add(user, fleet_id, jsonBody())), 201
    except usageWidgets.JobError as e:
        return widgetRefused(e)


@BPfleet.route('/fleets/<int:fleet_id>/widgets/order', methods=['PUT'])
@token_required
def widgetOrder(user, fleet_id):
    """`{ids}`: every widget of the fleet, once, in their new order"""
    try:
        return jsonify(usageWidgets.reorder(user, fleet_id, jsonBody()))
    except usageWidgets.JobError as e:
        return widgetRefused(e)


@BPfleet.route('/fleets/<int:fleet_id>/widgets/<int:widget_id>', methods=['PUT'])
@token_required
def widgetUpdate(user, fleet_id, widget_id):
    """`{display: total | servers}`"""
    try:
        return jsonify(usageWidgets.update(user, fleet_id, widget_id, jsonBody()))
    except usageWidgets.JobError as e:
        return widgetRefused(e)


@BPfleet.route('/fleets/<int:fleet_id>/widgets/<int:widget_id>', methods=['DELETE'])
@token_required
def widgetRemove(user, fleet_id, widget_id):
    try:
        usageWidgets.remove(user, fleet_id, widget_id)
        return jsonify({'deleted': widget_id})
    except usageWidgets.JobError as e:
        return widgetRefused(e)


@BPfleet.route('/fleets/<int:fleet_id>/widgets/<int:widget_id>/history', methods=['GET'])
@token_required
def widgetHistory(user, fleet_id, widget_id):
    """What the fleet's servers answered to the widget's saved query over `range` (as `/queries/saved/<id>/history`
    does), and `total`, their answers summed per hour or per day"""
    try:
        return jsonify(usageWidgets.history(user, fleet_id, widget_id, request.args.get('range')))
    except usageWidgets.JobError as e:
        return widgetRefused(e)
