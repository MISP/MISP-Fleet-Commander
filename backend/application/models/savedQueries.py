"""Saved queries: MispQL statements a user keeps, with where they run, how often, and what each server should answer.

A run of a saved query is an ordinary query run: a `mispql_query` job of the saved query's owner, on the owner's
servers (see models/fleetQueries.py). It therefore asks each server whether it runs complex queries right before
any search, like every other run. The job's parameters name the saved query; when the job ends, each server's
outcome is kept here (`SavedQueryResult`: the outcome, the count or number of rows, the summary), never the rows.

Whether a server's answer meets the expectation is decided when it is read, with the expectation as it is then.
Health (health/queries.py) raises an issue on each server whose last answer does not meet the expectation of a
scheduled saved query, or that could not be checked there. Every number a server answers is also kept over time
(models/savedQueryHistory.py), for the charts of the saved query.
"""
import time
from typing import Any, Dict, List, Optional

from flask import current_app

from application.DBModels import (SAVED_QUERY_COMPARATORS, SAVED_QUERY_SEVERITIES, Job, SavedQuery,
                                  SavedQueryResult, Server, db)
import application.models.jobs as jobModel
import application.models.userJobs as userJobs
from application.models import fleetQueries
from application.models import fleets as fleetModel
from application.models import savedQueryHistory
from application.models import setting as settingModel
from application.models.userJobs import JobError

MAX_NAME_LENGTH = 120
MAX_DESCRIPTION_LENGTH = 500
MAX_SAVED = 200
MAX_EXPECTED = 10 ** 12
# Minutes between scheduled runs
SCHEDULES = {15: 'Every 15 minutes', 60: 'Every hour', 360: 'Every 6 hours', 720: 'Every 12 hours',
             1440: 'Every day'}
# Statements whose answer is a number that can be checked, and that may therefore run on a schedule
CHECKED_KINDS = ('count', 'select')
COMPARATOR_SYMBOLS = {'eq': '=', 'ne': '≠', 'lt': '<', 'lte': '≤', 'gt': '>', 'gte': '≥'}
COMPARATOR_WORDS = {'eq': 'exactly', 'ne': 'anything but', 'lt': 'below', 'lte': 'at most', 'gt': 'above',
                    'gte': 'at least'}
# What a SELECT may expect: no rows, or some
ROW_EXPECTATIONS = {('eq', 0): 'no rows', ('gt', 0): 'some rows'}
# A run still queued or running after this long is taken as lost: the schedule starts the next one
LOST_RUN_SECONDS = 24 * 3600
UNFINISHED = ('queued', 'running')

# A server's state for a saved query
MET, UNMET, UNCHECKED, NOT_RUN, ANSWERED = 'met', 'unmet', 'unchecked', 'not_run', 'answered'
STATES = (MET, UNMET, UNCHECKED, NOT_RUN, ANSWERED)
# Outcomes that give the number an expectation is checked against
MEASURED = ('count', 'rows')


class SavedQueryError(JobError):
    """A refusal: `field` names the field at fault, `errors` the statement's mistakes placed on its text"""

    def __init__(self, message: str, status: int = 400, field: Optional[str] = None,
                 errors: Optional[List[dict]] = None):
        super().__init__(message, status)
        self.field = field
        self.errors = errors


# Checking what is saved

def ownedQuery(user):
    return SavedQuery.query.filter(SavedQuery.user_id == user.id)


def ownedSaved(user, savedId) -> SavedQuery:
    if isinstance(savedId, bool) or not isinstance(savedId, int):
        raise SavedQueryError('Unknown saved query', 404)
    saved = ownedQuery(user).filter(SavedQuery.id == savedId).first()
    if saved is None:
        raise SavedQueryError('Unknown saved query', 404)
    return saved


def checkedName(user, name: Any, exceptId: Optional[int] = None) -> str:
    if not isinstance(name, str) or name.strip() == '':
        raise SavedQueryError('A saved query needs a name', field='name')
    name = ' '.join(name.split())
    if len(name) > MAX_NAME_LENGTH:
        raise SavedQueryError(f'A name has at most {MAX_NAME_LENGTH} characters', field='name')
    taken = ownedQuery(user).filter(db.func.lower(SavedQuery.name) == name.lower())
    if exceptId is not None:
        taken = taken.filter(SavedQuery.id != exceptId)
    other = taken.first()
    if other is not None:
        raise SavedQueryError(f'You already have a saved query named “{other.name}”', 409, field='name')
    return name


def checkedDescription(description: Any) -> str:
    if description is None:
        return ''
    if not isinstance(description, str):
        raise SavedQueryError('`description` must be a text', field='description')
    description = description.strip()
    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise SavedQueryError(f'A description has at most {MAX_DESCRIPTION_LENGTH} characters', field='description')
    return description


def checkedStatement(statement: Any) -> fleetQueries.Prepared:
    """The statement as a run would take it; its mistakes are placed on its text"""
    try:
        return fleetQueries.prepare(statement)
    except fleetQueries.StatementError as e:
        raise SavedQueryError(e.errors[0]['message'], field='statement', errors=e.errors)


def checkedTarget(user, fleetId: Any, serverIds: Any):
    """(fleet_id, server_ids): one of them, the other None. A fleet is followed (its servers when a run starts);
    servers are kept as listed, in their order"""
    if (fleetId is None) == (serverIds is None):
        raise SavedQueryError('Give either `fleet_id` or `server_ids`', field='target')
    if fleetId is not None:
        if isinstance(fleetId, bool) or not isinstance(fleetId, int):
            raise SavedQueryError('`fleet_id` must be a fleet ID', field='target')
        if fleetModel.getForUser(user, fleetId) is None:
            raise SavedQueryError('Unknown fleet', 404, field='target')
        return fleetId, None
    try:
        ids = userJobs.parseServerIds(serverIds)
        userJobs.ownedServers(user, ids)
    except JobError as e:
        raise SavedQueryError(e.message, e.status, field='target')
    return None, ids


def checkedSchedule(value: Any, kind: str) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value not in SCHEDULES:
        raise SavedQueryError(f"`schedule_minutes` must be one of {', '.join(map(str, SCHEDULES))}, or null",
                              field='schedule_minutes')
    if kind not in CHECKED_KINDS:
        raise SavedQueryError('Only a SELECT or a COUNT can run on a schedule', field='schedule_minutes')
    return value


def checkedExpectation(value: Any, kind: str):
    """(comparator, expected), or (None, None) for no expectation"""
    if value is None:
        return None, None
    if not isinstance(value, dict):
        raise SavedQueryError('`expectation` must be `{"comparator", "value"}`, or null', field='expectation')
    comparator, expected = value.get('comparator'), value.get('value')
    if kind not in CHECKED_KINDS:
        raise SavedQueryError('Only a SELECT or a COUNT can have an expectation', field='expectation')
    if comparator not in SAVED_QUERY_COMPARATORS:
        raise SavedQueryError(f"`comparator` must be one of {', '.join(SAVED_QUERY_COMPARATORS)}",
                              field='expectation')
    if isinstance(expected, bool) or not isinstance(expected, int) or not 0 <= expected <= MAX_EXPECTED:
        raise SavedQueryError(f'The expected value must be a whole number from 0 to {MAX_EXPECTED}',
                              field='expectation')
    if kind == 'select' and (comparator, expected) not in ROW_EXPECTATIONS:
        raise SavedQueryError('A SELECT can expect no rows (`eq` 0) or some rows (`gt` 0); count them with '
                              'SELECT COUNT(*) to expect a number', field='expectation')
    return comparator, expected


def checkedSeverity(value: Any) -> str:
    if value is None:
        return 'warning'
    if value not in SAVED_QUERY_SEVERITIES:
        raise SavedQueryError(f"`severity` must be one of {', '.join(SAVED_QUERY_SEVERITIES)}", field='severity')
    return value


# Saving

def create(user, body: dict) -> SavedQuery:
    """`{name, description?, statement, fleet_id | server_ids, schedule_minutes?, expectation?, severity?}`"""
    if ownedQuery(user).count() >= MAX_SAVED:
        raise SavedQueryError(f'You can keep at most {MAX_SAVED} saved queries', 409)
    name = checkedName(user, body.get('name'))
    description = checkedDescription(body.get('description'))
    prepared = checkedStatement(body.get('statement'))
    fleetId, serverIds = checkedTarget(user, body.get('fleet_id'), body.get('server_ids'))
    schedule = checkedSchedule(body.get('schedule_minutes'), prepared.kind)
    comparator, expected = checkedExpectation(body.get('expectation'), prepared.kind)
    now = int(time.time())
    saved = SavedQuery(user_id=user.id, name=name, description=description, statement=body['statement'],
                       fleet_id=fleetId, server_ids=serverIds, schedule_minutes=schedule, comparator=comparator,
                       expected=expected, severity=checkedSeverity(body.get('severity')), created=now, updated=now)
    db.session.add(saved)
    db.session.commit()
    return saved


def update(user, savedId, body: dict) -> SavedQuery:
    """Any field of `create`. A new statement drops the results and the history kept for the old one; a new target
    drops the results of servers no longer in it, and keeps their history (not shown while they are out of it). A schedule or an expectation that does not suit the statement is refused. A scheduled
    saved query whose statement, servers or schedule change runs at the scheduler's next turn"""
    saved = ownedSaved(user, savedId)
    before = (saved.statement, saved.fleet_id, saved.server_ids, saved.schedule_minutes)
    if 'name' in body:
        saved.name = checkedName(user, body['name'], exceptId=saved.id)
    if 'description' in body:
        saved.description = checkedDescription(body['description'])
    statement = body['statement'] if 'statement' in body else saved.statement
    kind = checkedStatement(statement).kind if 'statement' in body else statementKind(saved.statement)
    if 'fleet_id' in body or 'server_ids' in body:
        saved.fleet_id, saved.server_ids = checkedTarget(user, body.get('fleet_id'), body.get('server_ids'))
    schedule = body['schedule_minutes'] if 'schedule_minutes' in body else saved.schedule_minutes
    saved.schedule_minutes = checkedSchedule(schedule, kind)
    if 'expectation' in body:
        saved.comparator, saved.expected = checkedExpectation(body['expectation'], kind)
    elif saved.comparator is not None:
        saved.comparator, saved.expected = checkedExpectation(
            {'comparator': saved.comparator, 'value': saved.expected}, kind)
    if 'severity' in body:
        saved.severity = checkedSeverity(body['severity'])
    if statement != saved.statement:
        saved.statement = statement
        saved.results = []
        savedQueryHistory.drop(saved.id)
    else:
        kept = {server.id for server in targetServers(saved)}
        saved.results = [result for result in saved.results if result.server_id in kept]
    if saved.schedule_minutes is not None and \
            before != (saved.statement, saved.fleet_id, saved.server_ids, saved.schedule_minutes):
        saved.last_run_at = None  # its last run answered something else
    saved.updated = int(time.time())
    db.session.commit()
    return saved


def delete(user, savedId) -> None:
    db.session.delete(ownedSaved(user, savedId))
    db.session.commit()


def statementKind(statement: str) -> Optional[str]:
    """What the statement is, whatever the current caps say of it; None when it no longer reads"""
    try:
        return fleetQueries.prepare(statement, max_limit=10 ** 9).kind
    except fleetQueries.StatementError:
        return None


def statementLimit(statement: str) -> Optional[int]:
    """The rows a run of this SELECT asks of each server now: its LIMIT, or the setting's when it has none"""
    try:
        prepared = fleetQueries.prepare(statement, max_limit=10 ** 9)
    except fleetQueries.StatementError:
        return None
    return fleetQueries.maxLimit() if prepared.limit_added else prepared.limit


def statementError(statement: str) -> Optional[dict]:
    """The first mistake a run would find in the statement now (a lowered cap), or None"""
    try:
        fleetQueries.prepare(statement)
    except fleetQueries.StatementError as e:
        return e.errors[0]
    return None


# Where it runs

def targetServers(saved: SavedQuery) -> List[Server]:
    """The owner's servers a run would query now: the fleet's, by name, or the listed ones still there, as listed"""
    if saved.fleet_id is not None:
        return Server.query.filter(Server.fleet_id == saved.fleet_id, Server.user_id == saved.user_id) \
            .order_by(Server.name, Server.id).all()
    ids = [serverId for serverId in (saved.server_ids or []) if isinstance(serverId, int)]
    if not ids:
        return []
    byId = {server.id: server for server in
            Server.query.filter(Server.id.in_(ids), Server.user_id == saved.user_id).all()}
    return [byId[serverId] for serverId in ids if serverId in byId]


def aims(check: dict, server) -> bool:
    """Whether a saved query (as `healthChecks` gives it) still runs on this server"""
    if check['fleet_id'] is not None:
        return getattr(server, 'fleet_id', None) == check['fleet_id']
    return server.id in (check['server_ids'] or [])


def noServersMessage(saved: SavedQuery) -> str:
    if saved.fleet_id is None and saved.server_ids is None:
        return 'Its fleet was deleted: choose where it runs'
    if saved.fleet_id is not None:
        return 'Its fleet has no servers'
    return 'None of its servers exist anymore'


# Runs

def lastJob(saved: SavedQuery) -> Optional[Job]:
    return db.session.get(Job, saved.last_job_id) if saved.last_job_id else None


def runInProgress(saved: SavedQuery, now: Optional[float] = None) -> bool:
    job = lastJob(saved)
    now = time.time() if now is None else now
    return job is not None and job.status in UNFINISHED and now - job.created < LOST_RUN_SECONDS


def startRun(saved: SavedQuery, now: Optional[int] = None) -> Job:
    """Queue a run of the saved query on its servers, as a query job of its owner. It counts as the last run"""
    servers = targetServers(saved)
    if not servers:
        raise SavedQueryError(noServersMessage(saved), 409)
    job = jobModel.create(saved.user, fleetQueries.KIND, servers,
                          params={'statement': saved.statement, 'saved_query_id': saved.id},
                          title=userJobs.defaultTitle(f'Saved query “{saved.name}”', servers),
                          fleet=userJobs.commonFleet(servers))
    saved.last_run_at = int(time.time()) if now is None else now
    saved.last_job_id = job.id
    saved.last_error = ''
    db.session.commit()
    return userJobs.enqueue(job)


def runNow(user, savedId) -> Job:
    """A run by hand. Refused while a run is in progress, or when the statement no longer passes the checks"""
    saved = ownedSaved(user, savedId)
    if runInProgress(saved):
        raise SavedQueryError('This saved query is already running', 409)
    checkedStatement(saved.statement)
    return startRun(saved)


def isDue(saved: SavedQuery, now: int) -> bool:
    if saved.schedule_minutes is None:
        return False
    return saved.last_run_at is None or saved.last_run_at + saved.schedule_minutes * 60 <= now


def nextRunAt(saved: SavedQuery) -> Optional[int]:
    if saved.schedule_minutes is None:
        return None
    if saved.last_run_at is None:
        return int(time.time())
    return saved.last_run_at + saved.schedule_minutes * 60


def runDue(now: Optional[int] = None) -> List[str]:
    """Start the scheduled saved queries that are due, unless scheduled runs are off. A saved query whose last run
    is still going waits for it. Returns the jobs started. A statement that no longer passes the checks (a lowered
    cap) still runs: each server then reports it as invalid, which health shows"""
    if not settingModel.getRefreshValue('query_schedule_enabled'):
        return []
    now = int(time.time()) if now is None else now
    started = []
    for saved in SavedQuery.query.filter(SavedQuery.schedule_minutes.isnot(None)).order_by(SavedQuery.id).all():
        if not isDue(saved, now) or runInProgress(saved, now):
            continue
        savedId = saved.id
        try:
            started.append(startRun(saved, now).id)
        except Exception as e:  # One saved query that cannot start must not hold the others back
            db.session.rollback()
            if not isinstance(e, JobError):
                current_app.logger.exception(f'Saved query {savedId}: the scheduled run could not start')
            saved = db.session.get(SavedQuery, savedId)
            if saved is None:
                continue
            # Tried again at the next turn of its schedule, not every minute
            saved.last_run_at = now
            saved.last_error = (e.message if isinstance(e, JobError) else f'Could not start: {e}')[:255]
            db.session.commit()
    return started


def recordRun(job: Job) -> List[Server]:
    """Keep each server's outcome of a finished run of a saved query. A run of a statement the saved query no
    longer holds (an old run retried) is not kept, nor an outcome older than the one kept. Units cancelled before
    they started leave the kept outcome alone. Returns the servers whose outcome changed"""
    params = job.secret_params or {}
    savedId = params.get('saved_query_id')
    saved = db.session.get(SavedQuery, savedId) if isinstance(savedId, int) else None
    if saved is None or saved.user_id != job.user_id or saved.statement != params.get('statement'):
        return []
    kept = {result.server_id: result for result in saved.results}
    touched = []
    for unit in job.results:
        if unit.server_id is None or unit.status not in ('ok', 'error', 'skipped'):
            continue
        summary = unit.response if isinstance(unit.response, dict) else {}
        outcome = summary.get('outcome')
        if not isinstance(outcome, str) or outcome == '':
            outcome = 'skipped' if unit.status == 'skipped' else 'failed'
        checkedAt = int(unit.finished or job.finished or time.time())
        result = kept.get(unit.server_id)
        if result is not None and result.checked_at > checkedAt:
            continue
        if result is None:
            result = SavedQueryResult(server_id=unit.server_id)
            saved.results.append(result)
        result.job_id = job.id
        result.outcome = outcome[:32]
        result.value = measuredValue(outcome, summary)
        result.more = bool(summary.get('more')) if outcome == 'rows' else False
        result.message = (unit.summary or '')[:500]
        result.checked_at = checkedAt
        if result.value is not None:
            savedQueryHistory.record(saved.id, unit.server_id, checkedAt, result.value, result.more)
        touched.append(unit.server_id)
    db.session.commit()
    if not touched:
        return []
    return Server.query.filter(Server.id.in_(touched)).all()


def measuredValue(outcome: str, summary: dict) -> Optional[int]:
    value = summary.get('count') if outcome == 'count' else summary.get('rows') if outcome == 'rows' else None
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def afterRun(job: Job) -> None:
    """Called when a query job ends: a run of a saved query keeps its outcomes, and the health of its servers is
    published again"""
    from application.models.health import publishServerHealth
    for server in recordRun(job):
        publishServerHealth(server)


# Judging an answer

def compare(comparator: str, value: int, expected: int) -> bool:
    return {
        'eq': value == expected, 'ne': value != expected, 'lt': value < expected,
        'lte': value <= expected, 'gt': value > expected, 'gte': value >= expected,
    }[comparator]


def judge(comparator: Optional[str], expected: Optional[int], result: Optional[dict]) -> str:
    """A server's state for a saved query, from its kept result (`outcome`, `value`)"""
    if result is None:
        return NOT_RUN
    if result['outcome'] not in MEASURED or result['value'] is None:
        return UNCHECKED
    if comparator is None:
        return ANSWERED
    return MET if compare(comparator, result['value'], expected) else UNMET


def expectationText(kind: Optional[str], comparator: Optional[str], expected: Optional[int]) -> Optional[str]:
    """"no rows", "some rows", "at most 5"…"""
    if comparator is None:
        return None
    if kind == 'select' and (comparator, expected) in ROW_EXPECTATIONS:
        return ROW_EXPECTATIONS[(comparator, expected)]
    return f'{COMPARATOR_WORDS[comparator]} {expected}'


def foundText(result: dict) -> str:
    """What a server answered, in words: "counted 12", "found 3 rows", "found 100 rows or more", "found none\""""
    value = result['value']
    if result['outcome'] == 'count':
        return f'counted {value}'
    if value == 0:
        return 'found none'
    noun = 'row' if value == 1 else 'rows'
    return f'found {value} {noun} or more' if result.get('more') else f'found {value} {noun}'


# History

def historyFor(user, savedId, rangeName: Optional[str], now: Optional[int] = None,
               servers: Optional[List[Server]] = None) -> dict:
    """What `GET /queries/saved/<id>/history` answers: each current server's numbers over the range (or only
    `servers`'), and the expectation they are drawn against"""
    saved = ownedSaved(user, savedId)
    try:
        rangeName = savedQueryHistory.parseRange(rangeName)
    except savedQueryHistory.HistoryRequestError as e:
        raise SavedQueryError(str(e), field='range')
    kind = statementKind(saved.statement)
    if kind not in CHECKED_KINDS:
        raise SavedQueryError('Only a SELECT or a COUNT answers a number to keep over time')
    servers = targetServers(saved) if servers is None else servers
    history = savedQueryHistory.series(saved.id, servers, saved.schedule_minutes, rangeName, now)
    history.update({
        'saved_query_id': saved.id,
        'kind': kind,
        'schedule_minutes': saved.schedule_minutes,
        'expectation': ({'comparator': saved.comparator, 'value': saved.expected}
                        if saved.comparator is not None else None),
        'expectation_text': expectationText(kind, saved.comparator, saved.expected),
        'limit': statementLimit(saved.statement) if kind == 'select' else None,
    })
    return history


# Health

def healthChecks(userId: int) -> Dict[int, List[dict]]:
    """Server ID → the saved queries of this user that are watched there (on a schedule, with an expectation), each
    with what the server last answered. Whether the server is still in its target is the caller's to check"""
    rows = db.session.query(SavedQuery, SavedQueryResult) \
        .join(SavedQueryResult, SavedQueryResult.saved_query_id == SavedQuery.id) \
        .filter(SavedQuery.user_id == userId, SavedQuery.schedule_minutes.isnot(None),
                SavedQuery.comparator.isnot(None)) \
        .order_by(SavedQuery.name, SavedQuery.id).all()
    kinds = {}
    checks = {}
    for saved, result in rows:
        if saved.id not in kinds:
            kinds[saved.id] = statementKind(saved.statement)
        checks.setdefault(result.server_id, []).append({
            'id': saved.id, 'name': saved.name, 'description': saved.description,
            'statement': saved.statement, 'kind': kinds[saved.id],
            'fleet_id': saved.fleet_id, 'server_ids': saved.server_ids,
            'comparator': saved.comparator, 'expected': saved.expected, 'severity': saved.severity,
            'result': serializeResult(result),
        })
    return checks


# Reading

def serializeResult(result: SavedQueryResult) -> dict:
    return {'outcome': result.outcome, 'value': result.value, 'more': result.more, 'message': result.message,
            'checked_at': result.checked_at, 'job_id': result.job_id}


def serverStates(saved: SavedQuery, servers: Optional[List[Server]] = None) -> List[dict]:
    """Each server the saved query runs on now, with what it last answered there and its state"""
    servers = targetServers(saved) if servers is None else servers
    kept = {result.server_id: serializeResult(result) for result in saved.results}
    states = []
    for server in servers:
        result = kept.get(server.id)
        states.append({'server_id': server.id, 'server_name': server.name, 'result': result,
                       'state': judge(saved.comparator, saved.expected, result)})
    return states


def serialize(saved: SavedQuery, withServers: bool = False) -> dict:
    kind = statementKind(saved.statement)
    servers = targetServers(saved)
    states = serverStates(saved, servers)
    overview = {state: 0 for state in STATES}
    for entry in states:
        overview[entry['state']] += 1
    job = lastJob(saved)
    fleet = saved.fleet_id and fleetModel.getForUser(saved.user, saved.fleet_id)
    data = {
        'id': saved.id,
        'name': saved.name,
        'description': saved.description,
        'statement': saved.statement,
        'kind': kind,
        'statement_error': statementError(saved.statement),
        'fleet_id': saved.fleet_id,
        'fleet_name': fleet.name if fleet else None,
        'server_ids': saved.server_ids,
        'server_count': len(servers),
        'schedule_minutes': saved.schedule_minutes,
        'expectation': ({'comparator': saved.comparator, 'value': saved.expected}
                        if saved.comparator is not None else None),
        'expectation_text': expectationText(kind, saved.comparator, saved.expected),
        'severity': saved.severity,
        'created': saved.created,
        'updated': saved.updated,
        'last_run_at': saved.last_run_at,
        'last_job_id': saved.last_job_id if job is not None else None,
        'last_job_status': job.status if job is not None else None,
        'running': runInProgress(saved),
        'next_run_at': nextRunAt(saved) if settingModel.getRefreshValue('query_schedule_enabled') else None,
        'last_error': saved.last_error or (noServersMessage(saved) if not servers else ''),
        'overview': overview,
    }
    if withServers:
        data['servers'] = states
    return data


def listForUser(user) -> List[dict]:
    return [serialize(saved) for saved in ownedQuery(user).order_by(db.func.lower(SavedQuery.name)).all()]


def options() -> dict:
    """What a saved query may hold, for the form that saves one"""
    return {
        'schedules': [{'minutes': minutes, 'label': label} for minutes, label in SCHEDULES.items()],
        'comparators': [{'name': name, 'symbol': COMPARATOR_SYMBOLS[name], 'words': COMPARATOR_WORDS[name]}
                        for name in SAVED_QUERY_COMPARATORS],
        'row_expectations': [{'comparator': comparator, 'value': value, 'label': label}
                             for (comparator, value), label in ROW_EXPECTATIONS.items()],
        'severities': list(SAVED_QUERY_SEVERITIES),
        'max_saved': MAX_SAVED,
        'scheduled_runs': bool(settingModel.getRefreshValue('query_schedule_enabled')),
    }
