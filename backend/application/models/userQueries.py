"""Fleet queries as the API offers them: a statement checked, run on the user's servers, and read back.

Runs are jobs (`fleetQueries.KIND`): the jobs API lists, cancels and retries them. Like any job, a run's statement and
per-server summaries are visible to admins; its rows only to the user who ran it, since they were fetched with that
user's keys.
"""
import concurrent.futures
from typing import List, Optional

import mispql
from flask import current_app
from mispql.compiler import RENDERINGS
from mispql.lexer import KEYWORDS

import application.models.jobs as jobModel
import application.models.userJobs as userJobs
from application.DBModels import Job, Server, db
from application.models import fleetQueries, queryCapability, savedQueries
from application.models import fleets as fleetModel
from application.models.userJobs import JobError

# Servers asked at the same time for their capability or a table's fields
LOOKUP_CONCURRENCY = 10


class StatementRefused(JobError):
    """The statement cannot run: its mistakes, placed on its text"""

    def __init__(self, errors: List[dict]):
        super().__init__(errors[0]['message'], 400)
        self.errors = errors


def serversFor(user, server_ids=None, fleet_id=None) -> List[Server]:
    """The user's servers named by `server_ids`, or every server of the user's fleet `fleet_id`"""
    if (server_ids is None) == (fleet_id is None):
        raise JobError('Give either `server_ids` or `fleet_id`')
    if fleet_id is None:
        return userJobs.ownedServers(user, userJobs.parseServerIds(server_ids))
    if isinstance(fleet_id, bool) or not isinstance(fleet_id, int):
        raise JobError('`fleet_id` must be a fleet ID')
    fleet = fleetModel.getForUser(user, fleet_id)
    if fleet is None:
        raise JobError('Unknown fleet', 404)
    servers = Server.query.filter(Server.fleet_id == fleet.id, Server.user_id == user.id) \
        .order_by(Server.name, Server.id).all()
    if not servers:
        raise JobError('This fleet has no servers', 409)
    return servers


def check(statement) -> dict:
    return fleetQueries.describeStatement(statement)


def language() -> dict:
    """What the editor highlights and completes, as mispql reads it: its keywords, each table's default columns,
    column aliases and sort names, the FORMATs read here, and the most rows a server may return. Also what a saved
    query may hold (schedules, comparators, severities)"""
    return {
        'keywords': sorted(KEYWORDS),
        'formats': list(RENDERINGS),
        'tables': [{  # a list, in mispql's order: JSON objects lose theirs
            'name': name,
            'columns': list(table.columns),
            'aliases': dict(table.aliases),
            'sortable': list(table.sortable),
        } for name, table in mispql.TABLES.items()],
        'max_limit': fleetQueries.maxLimit(),
        'saved': savedQueries.options(),
    }


def notes(prepared: fleetQueries.Prepared) -> List[str]:
    if prepared.limit_added:
        return [f'No LIMIT: each server returns at most {prepared.limit} rows']
    return []


def create(user, statement, server_ids=None, fleet_id=None, title=None):
    """(job, notes): the run, queued. The statement is checked first: nothing is created for one that cannot run"""
    try:
        prepared = fleetQueries.prepare(statement)
    except fleetQueries.StatementError as e:
        raise StatementRefused(e.errors)
    servers = serversFor(user, server_ids, fleet_id)
    if title is not None and not isinstance(title, str):
        raise JobError('`title` must be a text')
    title = (title or '').strip() or userJobs.defaultTitle(fleetQueries.title(statement), servers)
    job = jobModel.create(user, fleetQueries.KIND, servers, params={'statement': statement}, title=title,
                          fleet=userJobs.commonFleet(servers))
    return userJobs.enqueue(job), notes(prepared)


def getRun(user, job_id) -> Job:
    job = userJobs.getForUser(user, job_id)
    if job.kind != fleetQueries.KIND:
        raise JobError('Unknown query run', 404)
    return job


def summaryOf(result) -> dict:
    return result.response if isinstance(result.response, dict) else {}


def hasRows(result) -> bool:
    return result.server_id is not None and summaryOf(result).get('outcome') == 'rows'


def serializeRun(user, job: Job) -> dict:
    """The job with its per-server summaries, its statement, and for its owner which servers' rows are still kept"""
    serialized = jobModel.serializeJob(job, withResults=True)
    serialized['statement'] = (job.params or {}).get('statement')
    readable = job.user_id == user.id
    serialized['rows_readable'] = readable
    kept = fleetQueries.rowsKept(job.id, [r.server_id for r in job.results if hasRows(r)]) if readable else set()
    for result, entry in zip(job.results, serialized['results']):
        entry['rows_kept'] = (result.server_id in kept) if readable and hasRows(result) else None
    return serialized


def rows(user, job_id, offset: int = 0, limit: int = 100, server_id: Optional[int] = None) -> dict:
    """A page of the run's rows, every server's merged (or one server's), with the columns they have"""
    job = getRun(user, job_id)
    if job.user_id != user.id:
        raise JobError('Only the user who ran this query can read its rows', 403)
    if offset < 0:
        raise JobError('`offset` starts at 0')
    if not 1 <= limit <= fleetQueries.MAX_PAGE_SIZE:
        raise JobError(f'`limit` must be between 1 and {fleetQueries.MAX_PAGE_SIZE}')
    if server_id is not None and server_id not in [r.server_id for r in job.results]:
        raise JobError('This server is not part of this query run', 404)
    servers = [{'id': r.server_id, 'name': r.server_name} for r in job.results
               if hasRows(r) and (server_id is None or r.server_id == server_id)]
    merged = fleetQueries.merge((job.secret_params or {}).get('statement'), servers, job.id)
    return {
        'job_id': job.id,
        'columns': merged['columns'],
        'default_columns': merged['default_columns'],
        'rows': merged['rows'][offset:offset + limit],
        'total': len(merged['rows']),
        'offset': offset,
        'limit': limit,
        'expired_servers': merged['expired_servers'],
    }


def eachServer(servers: List[Server], lookup) -> List[dict]:
    """`lookup(server)` for each server, a few at a time, in the servers' order. Each runs in an app context of its
    own, with the server loaded in that context's session"""
    app = current_app._get_current_object()

    def one(server_id):
        with app.app_context():
            server = db.session.get(Server, server_id)
            return lookup(server)

    workers = max(1, min(LOOKUP_CONCURRENCY, len(servers)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        found = list(pool.map(one, [server.id for server in servers]))
    return [{'server_id': server.id, 'server_name': server.name, **answer} for server, answer in zip(servers, found)]


def capabilities(user, server_ids=None, fleet_id=None, refresh: bool = False) -> List[dict]:
    servers = serversFor(user, server_ids, fleet_id)
    return eachServer(servers, lambda server: queryCapability.get(server, refresh=refresh))


def describe(user, table, server_ids=None, fleet_id=None, refresh: bool = False) -> List[dict]:
    """Each server's fields of `table`, for completing statements"""
    if table not in mispql.TABLES:
        raise JobError(f"Unknown table: use {', '.join(mispql.TABLES)}")
    servers = serversFor(user, server_ids, fleet_id)
    return eachServer(servers, lambda server: queryCapability.describe(server, table, refresh=refresh))
