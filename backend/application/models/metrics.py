"""Collection of the usage metrics of the servers of monitored fleets, into `metric_samples`.

A collection reads every source of the catalogue from one server, one request after the other, and stores what it
could read as one `raw` row. Servers are collected in parallel (threads): the threads only talk to MISP, the rows are
written by the caller's thread, which owns the database session.

Logins are counted, never stored: each collection reads the login and failed-login entries of MISP's log since the
previous read and counts those above the last log id counted (the cursor). The first collection of a server reads
the past 90 days instead (fewer when MISP's 5000-entry limit is hit) and stores them as hourly counts.
"""
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional

from application import redisModel
from application.DBModels import db, MetricSample, MetricState
from application.controllers.utils import errorText, mispGetRequest, mispPostRequest
from application.models import metricCatalogue as catalogue
from application.models.servers import isDue, isUnanswered
import application.models.setting as settingModel
from application.models.syncActivity import readableLogError

HOUR = 3600
LOG_URL = '/admin/logs/index'
LOG_LIMIT = 5000
BACKFILL_DAYS = (90, 30, 14, 7)
# The log window of a regular collection reaches this far before the previous read, so that entries written while
# it ran are not missed (the cursor keeps them from being counted twice)
LOGIN_WINDOW_MARGIN_MINUTES = 10
LOGIN_WINDOW_MAX_MINUTES = 24 * 60
ERROR_MAX_LENGTH = 500


def monitoringSettings() -> dict:
    """Read on every call, so that changes made in the settings apply without restarting the workers"""
    return {
        'enabled': bool(settingModel.getRefreshValue('monitoring_enabled')),
        'interval': int(settingModel.getValue('monitoring_interval')) * 60,
        'max_concurrency': int(settingModel.getValue('health_max_concurrency')),
    }


@dataclass(frozen=True)
class Target:
    """What the request helpers need to reach a server, read from the model before leaving the session's thread"""
    id: int
    name: str
    url: str
    authkey: str
    skip_ssl: bool

    @classmethod
    def of(cls, server):
        return cls(server.id, server.name, server.url, server.authkey, bool(server.skip_ssl))


@dataclass(frozen=True)
class LoginState:
    cursor: Optional[int] = None
    backfilled: bool = False
    read_at: Optional[int] = None

    @classmethod
    def of(cls, state: Optional[MetricState]):
        if state is None:
            return cls()
        return cls(state.login_cursor, bool(state.logins_backfilled), state.logins_read_at)


def answerError(answer) -> Optional[str]:
    """Why a request helper's answer is a failure, or None"""
    if isinstance(answer, list):
        return None
    if not isinstance(answer, dict):
        return 'Unexpected answer'
    status = answer.get('_status_code') or 200
    if 'error' in answer:
        return errorText(answer['error']) or 'Request failed'
    if status >= 400:
        message = answer.get('message') or answer.get('name')
        return f'HTTP {status}: {message}' if isinstance(message, str) and message else f'HTTP {status}'
    return None


def request(target: Target, source: catalogue.Source):
    if source.method == 'POST':
        return mispPostRequest(target, source.url, dict(source.payload or {}))
    return mispGetRequest(target, source.url, nocache=True)


def requestLogs(target: Target, created: str):
    return mispPostRequest(target, LOG_URL, {
        'model': 'User',
        'action': list(catalogue.LOGIN_ACTIONS),
        'created': created,
        'limit': LOG_LIMIT,
    })


def countLogins(entries: list, cursor: Optional[int]) -> tuple:
    """(counts, new cursor) of the entries above the cursor"""
    counts = {key: 0 for key in catalogue.LOGIN_ACTIONS.values()}
    highest = cursor
    for entry in entries:
        if cursor is not None and entry.id <= cursor:
            continue
        counts[entry.key] += 1
        highest = entry.id if highest is None else max(highest, entry.id)
    return counts, highest


def loginWindowMinutes(state: LoginState, interval_seconds: int, now: int) -> int:
    since = (now - state.read_at) if state.read_at is not None else interval_seconds
    minutes = -(-max(since, 0) // 60) + LOGIN_WINDOW_MARGIN_MINUTES
    return int(min(minutes, LOGIN_WINDOW_MAX_MINUTES))


def readLogEntries(target: Target, created: str) -> tuple:
    """(entries, full, error): `full` when MISP returned as many entries as it may (some are then missing)"""
    answer = requestLogs(target, created)
    if answerError(answer) is not None:
        return None, False, f'Logins: {readableLogError(answer if isinstance(answer, dict) else {})}'
    try:
        entries = catalogue.parseLoginLogs(answer)
    except catalogue.UnreadableAnswer as e:
        return None, False, f'Logins: {e}'
    return entries, len(answer['data']) >= LOG_LIMIT, None


def readLogins(target: Target, state: LoginState, interval_seconds: int, now: int) -> dict:
    """{counts, cursor, hours, backfilled, error}: `counts` (None when the log could not be read) go into the raw
    sample, `hours` (backfill only) into hour rows"""
    if not state.backfilled:
        return backfillLogins(target, now)
    entries, full, error = readLogEntries(target, f'{loginWindowMinutes(state, interval_seconds, now)}m')
    if error is not None:
        return {'counts': None, 'error': error}
    counts, cursor = countLogins(entries, state.cursor)
    result = {'counts': counts, 'cursor': cursor, 'error': None}
    if full:
        result['error'] = f'Logins: more than {LOG_LIMIT} log entries since the previous collection, some were not counted'
    return result


def backfillLogins(target: Target, now: int) -> dict:
    """First read of a server's logins: the past 90 days (30, 14 or 7 when there are more than 5000 entries). Hours
    that are over become hour rows; the current hour's entries are counted in the first raw sample, which the hour
    roll-up will sum up with the next ones. Tried once (`backfilled`), even when it fails"""
    entries, full, days = None, False, None
    for days in BACKFILL_DAYS:
        entries, full, error = readLogEntries(target, f'{days}d')
        if error is not None:
            return {'counts': None, 'backfilled': True, 'error': error}
        if not full:
            break
    hourStart = now - now % HOUR
    hours = defaultdict(lambda: {key: 0 for key in catalogue.LOGIN_ACTIONS.values()})
    current = []
    for entry in entries:
        if entry.created is None or entry.created >= hourStart:
            current.append(entry)
        else:
            hours[entry.created - entry.created % HOUR][entry.key] += 1
    counts, _ = countLogins(current, None)
    cursor = max((entry.id for entry in entries), default=None)
    result = {'counts': counts, 'cursor': cursor, 'hours': dict(hours), 'backfilled': True, 'error': None}
    if full:
        result['error'] = f'Logins: more than {LOG_LIMIT} log entries over the past {days} days, some were not counted'
    return result


def fetchServerMetrics(target: Target, logins: LoginState, interval_seconds: int, now: Optional[int] = None) -> dict:
    """Read every source of one server. Runs outside the database session: MISP requests and parsing only.
    {values, errors, logins}. A server that does not answer the first request is not asked anything else"""
    now = int(time.time()) if now is None else now
    values, errors, answered = {}, [], False
    for index, source in enumerate(catalogue.SOURCES):
        answer = request(target, source)
        error = answerError(answer)
        if error is not None:
            errors.append(f'{source.label}: {error}')
            if index == 0 and isUnanswered(answer):
                return {'values': values, 'errors': errors, 'logins': None}
            continue
        answered = True
        try:
            for key, value in source.parse(answer).items():
                values.setdefault(key, value)
        except catalogue.UnreadableAnswer as e:
            errors.append(f'{source.label}: {e}')
    return {
        'values': values,
        'errors': errors,
        'logins': readLogins(target, logins, interval_seconds, now) if answered else None,
    }


def _upsert(server_id: int, tier: str, ts: int, values: dict, peaks: Optional[dict] = None, samples: int = 1):
    """Write a sample, merging its values into the row already there for that time"""
    row = MetricSample.query.filter_by(server_id=server_id, tier=tier, ts=ts).first()
    if row is None:
        row = MetricSample(server_id=server_id, tier=tier, ts=ts, values=dict(values), peaks=peaks, samples=samples)
        db.session.add(row)
    else:
        row.values = {**(row.values or {}), **values}
        if peaks is not None:
            row.peaks = {**(row.peaks or {}), **peaks}
    return row


def storeCollection(server_id: int, result: dict, now: Optional[int] = None) -> MetricState:
    """Save what a collection read: a raw row when anything was read, the backfilled hours, and the state"""
    now = int(time.time()) if now is None else now
    state = db.session.get(MetricState, server_id)
    if state is None:
        state = MetricState(server_id=server_id, logins_total=0, failed_logins_total=0, logins_backfilled=False)
        db.session.add(state)
    state.last_attempt = now
    values = dict(result.get('values') or {})
    errors = list(result.get('errors') or [])
    logins = result.get('logins') or {}
    if logins.get('backfilled'):
        state.logins_backfilled = True
    if logins.get('counts') is not None:
        values.update(logins['counts'])
        state.logins_total = (state.logins_total or 0) + logins['counts']['logins']
        state.failed_logins_total = (state.failed_logins_total or 0) + logins['counts']['failed_logins']
        if logins.get('cursor') is not None:
            state.login_cursor = logins['cursor']
        state.logins_read_at = now
    for bucket, counts in (logins.get('hours') or {}).items():
        _upsert(server_id, 'hour', int(bucket), counts, samples=0)
        state.logins_total += counts['logins']
        state.failed_logins_total += counts['failed_logins']
    if logins.get('error'):
        errors.append(logins['error'])
    if values:
        _upsert(server_id, 'raw', now, values)
        state.last_success = now
    elif not errors:
        errors.append('Nothing could be read')
    state.last_error = '; '.join(errors)[:ERROR_MAX_LENGTH] or None
    db.session.commit()
    return state


def monitoredServers(fleets) -> list:
    """Servers of the given fleets that can be queried (they have an API key)"""
    return [server for fleet in fleets for server in fleet.servers if server.authkey]


def statesOf(server_ids) -> dict:
    if not server_ids:
        return {}
    return {state.server_id: state for state in MetricState.query.filter(MetricState.server_id.in_(server_ids))}


def serversDueForCollection(servers: list, interval_seconds: int, now: int) -> list:
    states = statesOf([server.id for server in servers])
    return [server for server in servers
            if isDue(states[server.id].last_attempt if server.id in states else None, interval_seconds, now)]


def collect(servers: list, interval_seconds: int, max_concurrency: int, onCollected=None) -> list:
    """Collect the servers, at most `max_concurrency` at a time. Returns [(server, state)]; `onCollected(server,
    state)` is called as each one is stored. A failure on one server does not stop the others"""
    if not servers:
        return []
    states = statesOf([server.id for server in servers])
    jobs = [(server, Target.of(server), LoginState.of(states.get(server.id))) for server in servers]
    collected = []
    with ThreadPoolExecutor(max_workers=max(1, min(int(max_concurrency), len(jobs)))) as pool:
        futures = {pool.submit(fetchServerMetrics, target, logins, interval_seconds): server
                   for server, target, logins in jobs}
        for future in as_completed(futures):
            server = futures[future]
            try:
                result = future.result()
            except Exception as e:  # A bug in a parser must not lose the other servers' samples
                result = {'values': {}, 'errors': [f'Collection failed: {e}'], 'logins': None}
            try:
                state = storeCollection(server.id, result)
            except Exception as e:
                db.session.rollback()
                print(f'Could not store the metrics of server {server.id}: {e}')
                continue
            collected.append((server, state))
            if onCollected is not None:
                onCollected(server, state)
    return collected


def collectAndAnnounce(servers: list, interval_seconds: int, max_concurrency: int, socketioEmitter,
                       onCollected=None) -> list:
    """Collect the servers, then record when each of their fleets was monitored and tell the fleet owners"""
    collected = collect(servers, interval_seconds, max_concurrency, onCollected=onCollected)
    for fleet_id in sorted({server.fleet_id for server, _ in collected}):
        monitored_timestamp = redisModel.setFleetMonitoredTimestamp(fleet_id)
        if monitored_timestamp is not None:
            socketioEmitter.fleet_update_timestamps(fleet_id, monitored_timestamp=monitored_timestamp)
    return collected
