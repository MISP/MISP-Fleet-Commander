from flask import Blueprint, jsonify, request

from application.controllers.instance import token_required
from application.controllers.jobs import TRUE_VALUES, errorResponse, intArg, jsonBody
import application.models.jobs as jobModel
import application.models.userJobs as userJobs
import application.models.userQueries as userQueries

BPqueries = Blueprint('queries', __name__)


def statementRefused(error: userQueries.StatementRefused):
    return jsonify({'message': error.message, 'errors': error.errors}), 400


def serverIdsArg():
    """`server_ids` as `1,2,3`, or None when absent"""
    value = request.args.get('server_ids')
    if value is None or value.strip() == '':
        return None
    try:
        return [int(part) for part in value.split(',') if part.strip()]
    except ValueError:
        raise userJobs.JobError('`server_ids` must be server IDs separated by commas')


def flagArg(name) -> bool:
    return request.args.get(name, '').lower() in TRUE_VALUES


@BPqueries.route('/queries/check', methods=['POST'])
@token_required
def check(user):
    """What a statement is, or its mistakes on the text (`{statement}`). Nothing is sent to any server"""
    try:
        return jsonify(userQueries.check(jsonBody().get('statement')))
    except userJobs.JobError as e:
        return errorResponse(e)


@BPqueries.route('/queries/language', methods=['GET'])
@token_required
def language(user):
    """Keywords, tables (default columns, aliases, sort names), FORMATs and the LIMIT cap, for the editor"""
    return jsonify(userQueries.language())


@BPqueries.route('/queries', methods=['POST'])
@token_required
def create(user):
    """Run a statement: `{statement, server_ids | fleet_id, title?}`. Answers 202 with the queued job, or 400 with
    the statement's mistakes (`errors`, each with offsets) and no job"""
    try:
        body = jsonBody()
        job, notes = userQueries.create(user, body.get('statement'), server_ids=body.get('server_ids'),
                                        fleet_id=body.get('fleet_id'), title=body.get('title'))
        return jsonify({'job_id': job.id, 'job': jobModel.serializeJob(job, withResults=True), 'notes': notes}), 202
    except userQueries.StatementRefused as e:
        return statementRefused(e)
    except userJobs.JobError as e:
        return errorResponse(e)


@BPqueries.route('/queries/capabilities', methods=['GET'])
@token_required
def capabilities(user):
    """Whether each server runs complex queries: `server_ids` (comma-separated) or `fleet_id`, `refresh=1` to ask
    again rather than read the cache"""
    try:
        return jsonify({'servers': userQueries.capabilities(user, server_ids=serverIdsArg(),
                                                            fleet_id=intArg('fleet_id'), refresh=flagArg('refresh'))})
    except userJobs.JobError as e:
        return errorResponse(e)


@BPqueries.route('/queries/describe', methods=['GET'])
@token_required
def describe(user):
    """Each server's fields of a table, for completing statements: `table`, `server_ids` or `fleet_id`, `refresh`"""
    try:
        return jsonify({'table': request.args.get('table'), 'servers': userQueries.describe(
            user, request.args.get('table'), server_ids=serverIdsArg(), fleet_id=intArg('fleet_id'),
            refresh=flagArg('refresh'))})
    except userJobs.JobError as e:
        return errorResponse(e)


@BPqueries.route('/queries/<job_id>', methods=['GET'])
@token_required
def view(user, job_id):
    """A run: its statement, and each server's summary (outcome, counts, located errors) and whether its rows are
    still kept"""
    try:
        return jsonify(userQueries.serializeRun(user, userQueries.getRun(user, job_id)))
    except userJobs.JobError as e:
        return errorResponse(e)


@BPqueries.route('/queries/<job_id>/rows', methods=['GET'])
@token_required
def rows(user, job_id):
    """A page of a run's rows, every server's merged: `offset`, `limit` (up to 1000), `server_id` for one server's.
    Only the user who ran it may read them"""
    try:
        return jsonify(userQueries.rows(user, job_id, offset=intArg('offset', 0), limit=intArg('limit', 100),
                                        server_id=intArg('server_id')))
    except userJobs.JobError as e:
        return errorResponse(e)
