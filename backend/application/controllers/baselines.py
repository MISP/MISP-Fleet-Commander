from flask import Blueprint, jsonify, request

from application.controllers.instance import token_required
import application.models.baselines as baselineModel

BPbaselines = Blueprint('baselines', __name__)


def errorResponse(error: baselineModel.BaselineError):
    return jsonify(error.toDict()), error.status


def jsonBody() -> dict:
    body = request.get_json(silent=True)
    if body is None:
        return {}
    if not isinstance(body, dict):
        raise baselineModel.BaselineError('The body must be a JSON object')
    return body


@BPbaselines.route('/baselines/types', methods=['GET'])
@token_required
def types(user):
    """Rule types, their comparators and value kinds, severities, and the server-specific settings"""
    return jsonify(baselineModel.ruleTypes())


@BPbaselines.route('/baselines/fleet/<int:fleet_id>', methods=['GET'])
@token_required
def view(user, fleet_id):
    """The fleet's baseline and its rules. A fleet without a baseline has no rules and no ID"""
    try:
        return jsonify(baselineModel.getForUser(user, fleet_id))
    except baselineModel.BaselineError as e:
        return errorResponse(e)


@BPbaselines.route('/baselines/fleet/<int:fleet_id>', methods=['DELETE'])
@token_required
def deleteBaseline(user, fleet_id):
    """Removes the fleet's baseline with all its rules"""
    try:
        return jsonify(baselineModel.deleteRules(user, fleet_id, None))
    except baselineModel.BaselineError as e:
        return errorResponse(e)


@BPbaselines.route('/baselines/fleet/<int:fleet_id>/rules', methods=['POST'])
@token_required
def addRules(user, fleet_id):
    """`{rules: [{type, key, expected, comparator?, severity?, note?, label?, force?}], on_conflict?}`. All rules
    are added or none: invalid ones are listed in `errors` with their index. `on_conflict` decides for rules already
    in the baseline: `error` (409, default), `skip` or `replace`"""
    try:
        body = jsonBody()
        return jsonify(baselineModel.addRules(user, fleet_id, body.get('rules'),
                                              body.get('on_conflict') or 'error')), 201
    except baselineModel.BaselineError as e:
        return errorResponse(e)


@BPbaselines.route('/baselines/fleet/<int:fleet_id>/rules/delete', methods=['POST'])
@token_required
def deleteRules(user, fleet_id):
    """`{rule_ids: [...]}`"""
    try:
        body = jsonBody()
        if 'rule_ids' not in body:
            raise baselineModel.BaselineError('`rule_ids` is required', field='rule_ids')
        return jsonify(baselineModel.deleteRules(user, fleet_id, body['rule_ids']))
    except baselineModel.BaselineError as e:
        return errorResponse(e)


@BPbaselines.route('/baselines/fleet/<int:fleet_id>/copy', methods=['POST'])
@token_required
def copy(user, fleet_id):
    """`{from_fleet_id, mode?}`: `replace` (default) makes the rules identical to the other fleet's, `merge` adds
    them, overwriting rules with the same type and key"""
    try:
        body = jsonBody()
        return jsonify(baselineModel.copyFromFleet(user, fleet_id, body.get('from_fleet_id'),
                                                   body.get('mode') or 'replace'))
    except baselineModel.BaselineError as e:
        return errorResponse(e)


@BPbaselines.route('/baselines/rules/<int:rule_id>', methods=['PUT'])
@token_required
def updateRule(user, rule_id):
    """Changes `expected`, `comparator`, `severity`, `note`, `label` or `force`; the type and key are fixed"""
    try:
        return jsonify(baselineModel.updateRule(user, rule_id, jsonBody()))
    except baselineModel.BaselineError as e:
        return errorResponse(e)


@BPbaselines.route('/baselines/rules/<int:rule_id>', methods=['DELETE'])
@token_required
def deleteRule(user, rule_id):
    try:
        baselineModel.deleteRule(user, rule_id)
    except baselineModel.BaselineError as e:
        return errorResponse(e)
    return jsonify({'id': rule_id})
