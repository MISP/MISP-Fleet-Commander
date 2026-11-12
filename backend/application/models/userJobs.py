#!/usr/bin/env python3
"""Jobs as the API offers them: created, listed, cancelled and retried by their owner"""

from typing import List, Optional, Tuple

from sqlalchemy import func

import application
import application.models.jobRunner as jobRunner
import application.models.jobs as jobModel
from application.DBModels import Job, JobResult, Server, db
from application.models.jobUnits import isRelativePath
from application.models.plugins import getPluginFromID

# Kinds a client may start on several servers. Others are recorded by the app itself (single-server writes) or
# started by features of their own (baseline remediation)
API_KINDS = ('plugin_action', 'plugin_quick_action', 'rest_query')
MAX_SERVERS = 1000
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100
UNFINISHED = ('queued', 'running')


class JobError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def parseServerIds(server_ids) -> List[int]:
    if not isinstance(server_ids, list) or len(server_ids) == 0:
        raise JobError('`server_ids` must be a non-empty list of server IDs')
    ids = []
    for server_id in server_ids:
        if isinstance(server_id, bool) or not isinstance(server_id, int):
            raise JobError('`server_ids` must be a non-empty list of server IDs')
        if server_id not in ids:
            ids.append(server_id)
    if len(ids) > MAX_SERVERS:
        raise JobError(f'A job can target at most {MAX_SERVERS} servers')
    return ids


def ownedServers(user, server_ids: List[int]) -> List[Server]:
    """The servers, in the order given. Unknown servers and servers of other users are refused alike"""
    servers = Server.query.filter(Server.id.in_(server_ids), Server.user_id == user.id).all()
    byId = {server.id: server for server in servers}
    missing = [server_id for server_id in server_ids if server_id not in byId]
    if missing:
        raise JobError(f"Unknown server{'s' if len(missing) > 1 else ''}: {', '.join(map(str, missing))}", 404)
    return [byId[server_id] for server_id in server_ids]


def checkParams(kind: str, params) -> Tuple[dict, str]:
    """(params, default title stem). Refuses what could not run on any server"""
    if not isinstance(params, dict):
        raise JobError('`params` must be an object')
    if kind in ('plugin_action', 'plugin_quick_action'):
        plugin = getPluginFromID(application.loadedPlugins or [], params.get('plugin_id'))
        quick = kind == 'plugin_quick_action'
        if plugin is None:
            raise JobError(f"Unknown plugin `{params.get('plugin_id')}`")
        if not plugin.get('features', {}).get('quickAction' if quick else 'action'):
            raise JobError(f"Plugin `{plugin['id']}` has no {'quick action' if quick else 'action'}")
        if params.get('data') is not None and not isinstance(params.get('data'), dict):
            raise JobError('`params.data` must be an object')
        label = plugin['quickActionMeta']['quickActionName'] if quick else plugin['name']
        return {'plugin_id': plugin['id'], 'data': params.get('data') or {}}, label
    if kind == 'rest_query':
        method = str(params.get('method') or 'GET').upper()
        if method not in ('GET', 'POST'):
            raise JobError('`params.method` must be GET or POST')
        if not isRelativePath(params.get('url')):
            raise JobError('`params.url` must be a path on the MISP server, such as /servers/getVersion')
        data = params.get('data')
        if data is not None and not isinstance(data, (str, dict, list)):
            raise JobError('`params.data` must be a JSON text or value')
        return {'method': method, 'url': params['url'].strip(), 'data': data}, f"{method} {params['url'].strip()}"
    raise JobError(f"`kind` must be one of: {', '.join(API_KINDS)}")


def commonFleet(servers: List[Server]):
    fleetIds = {server.fleet_id for server in servers}
    return servers[0].fleet if len(fleetIds) == 1 else None


def defaultTitle(stem: str, servers: List[Server]) -> str:
    if len(servers) == 1:
        return f'{stem} on {servers[0].name}'
    return f'{stem} on {len(servers)} servers'


def enqueue(job: Job) -> Job:
    """Hand the job to the workers. If they cannot be reached, the job fails at once rather than staying queued"""
    from application.workers.tasks import runJob
    try:
        runJob(job.id)
    except Exception as e:
        application.flaskApp.logger.error(f'Could not queue job {job.id}: {e}')
        for result in job.results:
            if result.status == 'pending':
                jobModel.recordResult(result, 'error', summary='Not started: the workers could not be reached',
                                      commit=False)
        jobModel.finish(job)
        raise JobError('The job could not be started: the workers could not be reached', 503)
    return job


def createForUser(user, kind, server_ids, params, title=None) -> Job:
    if kind not in API_KINDS:
        raise JobError(f"`kind` must be one of: {', '.join(API_KINDS)}")
    servers = ownedServers(user, parseServerIds(server_ids))
    params, stem = checkParams(kind, params if params is not None else {})
    if title is not None and not isinstance(title, str):
        raise JobError('`title` must be a text')
    title = (title or '').strip() or defaultTitle(stem, servers)
    job = jobModel.create(user, kind, servers, params=params, title=title, fleet=commonFleet(servers))
    return enqueue(job)


def getForUser(user, job_id) -> Job:
    job = db.session.get(Job, job_id) if isinstance(job_id, str) else None
    if job is None or job.user_id != user.id:
        raise JobError('Unknown job', 404)
    return job


def parseChoices(value: Optional[str], allowed, name: str) -> Optional[List[str]]:
    if value is None or value.strip() == '':
        return None
    choices = [choice.strip() for choice in value.split(',') if choice.strip()]
    unknown = [choice for choice in choices if choice not in allowed]
    if unknown:
        raise JobError(f"Unknown `{name}`: {', '.join(unknown)}")
    return choices


def doneCounts(job_ids: List[str]) -> dict:
    """job_id → number of results that are over, in one query"""
    if not job_ids:
        return {}
    rows = db.session.query(JobResult.job_id, func.count(JobResult.id)) \
        .filter(JobResult.job_id.in_(job_ids), JobResult.status != 'pending') \
        .group_by(JobResult.job_id).all()
    return dict(rows)


def listForUser(user, fleet_id=None, server_id=None, status=None, kind=None, page=1, limit=DEFAULT_PAGE_SIZE) -> dict:
    """The user's jobs, newest first, a page at a time. `status` and `kind` take comma-separated values"""
    from application.DBModels import JOB_KINDS, JOB_STATUSES
    statuses = parseChoices(status, JOB_STATUSES, 'status')
    kinds = parseChoices(kind, JOB_KINDS, 'kind')
    if page < 1:
        raise JobError('`page` starts at 1')
    if not 1 <= limit <= MAX_PAGE_SIZE:
        raise JobError(f'`limit` must be between 1 and {MAX_PAGE_SIZE}')
    query = Job.query.filter(Job.user_id == user.id)
    if fleet_id is not None:
        query = query.filter(Job.fleet_id == fleet_id)
    if server_id is not None:
        query = query.filter(Job.results.any(JobResult.server_id == server_id))
    if statuses:
        query = query.filter(Job.status.in_(statuses))
    if kinds:
        query = query.filter(Job.kind.in_(kinds))
    total = query.count()
    jobs = query.order_by(Job.created.desc()).offset((page - 1) * limit).limit(limit).all()
    done = doneCounts([job.id for job in jobs])
    serialized = []
    for job in jobs:
        entry = jobModel.serializeJob(job)
        entry['done'] = done.get(job.id, 0)
        serialized.append(entry)
    return {'jobs': serialized, 'total': total, 'page': page, 'limit': limit}


def cancel(user, job_id) -> Job:
    job = getForUser(user, job_id)
    if job.status not in UNFINISHED:
        raise JobError('This job is over: there is nothing left to cancel', 409)
    jobRunner.requestCancel(job.id)
    return job


def retry(user, job_id, only_failed=True) -> Job:
    """A new job with the same parameters, on the servers that failed (or on all of them), skipping servers that
    were deleted since"""
    job = getForUser(user, job_id)
    if job.status in UNFINISHED:
        raise JobError('This job is still running', 409)
    rows = [row for row in job.results if row.server_id is not None and (not only_failed or row.status == 'error')]
    servers = Server.query.filter(Server.id.in_([row.server_id for row in rows]), Server.user_id == user.id).all()
    byId = {server.id: server for server in servers}
    servers = [byId[row.server_id] for row in rows if row.server_id in byId]
    if not servers:
        raise JobError('No server left to retry' if only_failed else 'None of these servers exist anymore', 409)
    title = job.title if job.title.startswith('Retry: ') else f'Retry: {job.title}'
    newJob = jobModel.create(user, job.kind, servers, params=job.secret_params, title=title,
                             fleet=commonFleet(servers))
    return enqueue(newJob)
