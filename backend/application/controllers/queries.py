from flask import Blueprint, jsonify, request

from application.controllers.instance import token_required
from application.controllers.jobs import TRUE_VALUES, errorResponse, intArg, jsonBody
import application.models.jobs as jobModel
import application.models.userJobs as userJobs
import application.models.userQueries as userQueries
from application.models import savedQueries

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

# Saved queries

def savedQueryRefused(error: userJobs.JobError):
    body = {'message': error.message}
    if getattr(error, 'field', None):
        body['field'] = error.field
    if getattr(error, 'errors', None):
        body['errors'] = error.errors
    return jsonify(body), error.status


@BPqueries.route('/queries/saved', methods=['GET'])
@token_required
def savedIndex(user):
    """The user's saved queries, each with how its servers last answered (`overview`: met, unmet, unchecked…)"""
    return jsonify({'saved': savedQueries.listForUser(user)})


@BPqueries.route('/queries/saved', methods=['POST'])
@token_required
def savedCreate(user):
    """Save a statement: `{name, description?, statement, fleet_ids?, server_ids?, schedule_minutes?, expectation?:
    {comparator, value}, severity?}`: it runs on the followed fleets' servers and the servers listed, at least one
    of the two. 400 with `field`, or the statement's mistakes in `errors`"""
    try:
        saved = savedQueries.create(user, jsonBody())
        return jsonify(savedQueries.serialize(saved, withServers=True)), 201
    except userJobs.JobError as e:
        return savedQueryRefused(e)


@BPqueries.route('/queries/saved/<int:saved_id>', methods=['GET'])
@token_required
def savedView(user, saved_id):
    """A saved query, with each of its servers' last answer and state"""
    try:
        return jsonify(savedQueries.serialize(savedQueries.ownedSaved(user, saved_id), withServers=True))
    except userJobs.JobError as e:
        return savedQueryRefused(e)


@BPqueries.route('/queries/saved/<int:saved_id>', methods=['PUT'])
@token_required
def savedUpdate(user, saved_id):
    """Change any field given at creation. A new statement forgets the answers and the history kept for the old
    one"""
    try:
        saved = savedQueries.update(user, saved_id, jsonBody())
        return jsonify(savedQueries.serialize(saved, withServers=True))
    except userJobs.JobError as e:
        return savedQueryRefused(e)


@BPqueries.route('/queries/saved/<int:saved_id>', methods=['DELETE'])
@token_required
def savedDelete(user, saved_id):
    try:
        savedQueries.delete(user, saved_id)
        return jsonify({'deleted': saved_id})
    except userJobs.JobError as e:
        return savedQueryRefused(e)


@BPqueries.route('/queries/saved/<int:saved_id>/run', methods=['POST'])
@token_required
def savedRun(user, saved_id):
    """Run a saved query now, as a query job: 202 with the job. 409 while it is already running"""
    try:
        job = savedQueries.runNow(user, saved_id)
        return jsonify({'job_id': job.id, 'job': jobModel.serializeJob(job, withResults=True)}), 202
    except userJobs.JobError as e:
        return savedQueryRefused(e)


@BPqueries.route('/queries/saved/<int:saved_id>/history', methods=['GET'])
@token_required
def savedHistory(user, saved_id):
    """The numbers each of the saved query's servers answered over `range` (24h, 7d, 30d, 90d, 1y; 7d by default):
    every answer up to 7 days, per hour for 30 days, per day beyond, with the expectation to draw them against.
    400 for a DESCRIBE or SHOW TABLES, which answer no number"""
    try:
        return jsonify(savedQueries.historyFor(user, saved_id, request.args.get('range')))
    except userJobs.JobError as e:
        return savedQueryRefused(e)
