from flask import Blueprint, jsonify, request

from application.controllers.instance import token_required
import application.models.health as healthModel

BPhealth = Blueprint('health', __name__)

TRUE_VALUES = ('1', 'true', 'yes', 'on')


def errorResponse(error: healthModel.HealthError):
    return jsonify({'message': error.message}), error.status


def intArg(name):
    value = request.args.get(name)
    if value is None or value == '':
        return None
    try:
        return int(value)
    except ValueError:
        raise healthModel.HealthError(f'`{name}` must be an integer')


@BPhealth.route('/health/issues', methods=['GET'])
@token_required
def issues(user):
    """Current issues of the user's servers, most severe first, then oldest first. Acknowledged issues are left out
    unless `include_acked` is set. `severity` and `category` take comma-separated values"""
    try:
        return jsonify(healthModel.issuesForUser(
            user,
            fleet_id=intArg('fleet_id'),
            server_id=intArg('server_id'),
            severity=request.args.get('severity'),
            category=request.args.get('category'),
            include_acked=request.args.get('include_acked', '').lower() in TRUE_VALUES,
        ))
    except healthModel.HealthError as e:
        return errorResponse(e)


@BPhealth.route('/health/summary', methods=['GET'])
@token_required
def summary(user):
    return jsonify(healthModel.summaryForUser(user))


@BPhealth.route('/health/ack', methods=['POST'])
@token_required
def acknowledge(user):
    """Hide an issue until `until` (UNIX timestamp; empty: until the issue clears) with an optional `note`"""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get('issue_id'), str):
        return jsonify({'message': '`issue_id` is required'}), 400
    try:
        return jsonify(healthModel.acknowledge(user, payload['issue_id'], payload.get('until'), payload.get('note')))
    except healthModel.HealthError as e:
        return errorResponse(e)


@BPhealth.route('/health/ack/<path:issue_id>', methods=['DELETE'])
@token_required
def unacknowledge(user, issue_id):
    try:
        healthModel.unacknowledge(user, issue_id)
    except healthModel.HealthError as e:
        return errorResponse(e)
    return jsonify({'issue_id': issue_id})
