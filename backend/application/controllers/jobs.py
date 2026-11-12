from flask import Blueprint, jsonify, request

from application.controllers.instance import token_required
import application.models.jobs as jobModel
import application.models.userJobs as userJobs

BPjobs = Blueprint('jobs', __name__)

TRUE_VALUES = (True, 1, '1', 'true', 'yes', 'on')


def errorResponse(error: userJobs.JobError):
    return jsonify({'message': error.message}), error.status


def intArg(name, default=None):
    value = request.args.get(name)
    if value is None or value == '':
        return default
    try:
        return int(value)
    except ValueError:
        raise userJobs.JobError(f'`{name}` must be an integer')


def jsonBody() -> dict:
    body = request.get_json(silent=True)
    if body is None:
        return {}
    if not isinstance(body, dict):
        raise userJobs.JobError('The body must be a JSON object')
    return body


@BPjobs.route('/jobs', methods=['POST'])
@token_required
def create(user):
    """Start a job: `{kind, server_ids, params, title?}`. Answers 202 with the queued job and its pending results"""
    try:
        body = jsonBody()
        job = userJobs.createForUser(user, body.get('kind'), body.get('server_ids'), body.get('params'),
                                     body.get('title'))
        return jsonify({'job_id': job.id, 'job': jobModel.serializeJob(job, withResults=True)}), 202
    except userJobs.JobError as e:
        return errorResponse(e)


@BPjobs.route('/jobs', methods=['GET'])
@token_required
def index(user):
    """The user's jobs, newest first: `fleet_id`, `server_id`, `status` and `kind` (comma-separated), `q` (title,
    user, fleet or server name), `since` (UNIX time), `page`, `limit`. Admins may ask for `scope=all`: the jobs of
    every user, deleted users included"""
    try:
        return jsonify(userJobs.listForUser(
            user,
            fleet_id=intArg('fleet_id'),
            server_id=intArg('server_id'),
            status=request.args.get('status'),
            kind=request.args.get('kind'),
            page=intArg('page', 1),
            limit=intArg('limit', userJobs.DEFAULT_PAGE_SIZE),
            scope=request.args.get('scope') or 'mine',
            q=request.args.get('q'),
            since=intArg('since'),
        ))
    except userJobs.JobError as e:
        return errorResponse(e)


@BPjobs.route('/jobs/<job_id>', methods=['GET'])
@token_required
def view(user, job_id):
    try:
        return jsonify(jobModel.serializeJob(userJobs.getForUser(user, job_id), withResults=True))
    except userJobs.JobError as e:
        return errorResponse(e)


@BPjobs.route('/jobs/<job_id>/cancel', methods=['POST'])
@token_required
def cancel(user, job_id):
    """Servers not started yet are skipped; those in progress finish. JOB_DONE tells when the job is over"""
    try:
        job = userJobs.cancel(user, job_id)
        return jsonify({'job_id': job.id, 'status': job.status, 'cancel_requested': True}), 202
    except userJobs.JobError as e:
        return errorResponse(e)


@BPjobs.route('/jobs/<job_id>/retry', methods=['POST'])
@token_required
def retry(user, job_id):
    """A new job with the same parameters: `{only_failed: true}` (default) on the servers that failed, else on all.
    Only the job's owner may retry it (403 for an admin looking at someone else's job)"""
    try:
        body = jsonBody()
        onlyFailed = body.get('only_failed', True) in TRUE_VALUES
        job = userJobs.retry(user, job_id, only_failed=onlyFailed)
        return jsonify({'job_id': job.id, 'job': jobModel.serializeJob(job, withResults=True)}), 202
    except userJobs.JobError as e:
        return errorResponse(e)
