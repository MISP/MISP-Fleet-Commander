"""Recent sync activity of a server, read from its MISP logs: the pulls and pushes it ran against each of its sync
servers, with what they transferred and the runs that failed.

MISP logs one entry per run, with `model: Server` and `model_id` = the id of the sync server on that MISP (the remote
of the link). The titles and counters have changed across versions, so the parser reads them loosely:
- pull: `Pull from <url> initiated by <who>`, change `N events, N proposals[, N sightings][, N galaxy clusters]
  [, N analyst data] and N <last> pulled or updated. N events failed or didn't need an update.`
- push: `Push to <url> initiated by <who>`, change `N events pushed or updated. N events failed or didn't need an
  update.[ N collections pushed.]`
- failed pull (`action: error`): `Failed pull from <url> initiated by <who>`, change = the reason
- failed push (`action: error`): `Failed: Push to <url> initiated by <who>`, change `Push to server N failed. Reason:
  <reason>`
Per-event failures (`Failed to pull event #N.`) are not read: the run's own entry already counts them.

MISP stores log times in its own timezone, which the API does not tell: they are read as UTC.
"""
import json
import re
import time
from datetime import datetime, timezone
from typing import Optional

from application.redisModel import KEY_SYNC_ACTIVITY, redisClient
from application.controllers.utils import mispPostRequest

CACHE_SECONDS = 10 * 60
WINDOW_DAYS = 7
# When the window holds more entries than this, the last day is read instead (the API cannot sort, it returns the
# oldest entries first)
MAX_ENTRIES = 5000
REQUEST_TIMEOUT = 30
DAY = 24 * 3600
TITLE_FILTERS = ['Pull from %', 'Push to %', 'Failed pull from %', 'Failed: Push to %']
PULL_COUNTERS = ('events', 'proposals', 'sightings', 'galaxy_clusters', 'analyst_data', 'collections')
ERROR_MAX_LENGTH = 300

TITLE_RE = re.compile(r'^(?P<kind>Failed pull from|Failed: Push to|Pull from|Push to) (?P<url>\S+) initiated by ')
PULL_CHANGE_RE = re.compile(r'^(?P<counts>.*?) pulled or updated\.\s*(?P<failed>\d+) events? failed')
COUNT_RE = re.compile(r'(\d+) ([A-Za-z][A-Za-z ]*?)(?:,\s*|\s+and\s+|$)')
PUSH_CHANGE_RE = re.compile(r'^(?P<pushed>\d+) events? pushed or updated\.\s*(?P<failed>\d+) events? failed')
PUSH_COLLECTIONS_RE = re.compile(r'(?P<collections>\d+) collections? pushed')
PUSH_FAILURE_PREFIX_RE = re.compile(r'^Push to server \S+ failed\. Reason:\s*')


def _emptyDirection(counters, buckets):
    return {
        'runs': 0,
        'failures': 0,
        'last_run': None,
        'last_success': None,
        'last_failure': None,
        'last_error': None,
        'totals': {counter: 0 for counter in counters},
        # Oldest first; the last one covers the past 24 hours
        'daily': [{'runs': 0, 'failures': 0, 'events': 0} for _ in range(buckets)],
    }


def _parseCreated(created) -> Optional[int]:
    try:
        return int(datetime.strptime(str(created), '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp())
    except ValueError:
        return None


def _counterName(label: str) -> str:
    name = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', label.strip()).lower().replace(' ', '_')
    name = {'galaxyclusters': 'galaxy_clusters', 'analystdata': 'analyst_data'}.get(name.replace('_', ''), name)
    return f'{name}s' if f'{name}s' in PULL_COUNTERS else name


def parsePullChange(change: str) -> Optional[dict]:
    match = PULL_CHANGE_RE.search(change or '')
    if match is None:
        return None
    counts = {counter: 0 for counter in PULL_COUNTERS}
    for value, label in COUNT_RE.findall(match.group('counts')):
        name = _counterName(label)
        if name in counts:
            counts[name] = int(value)
    counts['events_failed'] = int(match.group('failed'))
    return counts


def parsePushChange(change: str) -> Optional[dict]:
    match = PUSH_CHANGE_RE.search(change or '')
    if match is None:
        return None
    collections = PUSH_COLLECTIONS_RE.search(change)
    return {
        'events': int(match.group('pushed')),
        'events_failed': int(match.group('failed')),
        'collections': int(collections.group('collections')) if collections else 0,
    }


def _failureMessage(kind: str, change: str) -> str:
    message = (change or '').strip()
    if kind == 'Failed: Push to':
        message = PUSH_FAILURE_PREFIX_RE.sub('', message)
    message = message or 'No reason given'
    return message if len(message) <= ERROR_MAX_LENGTH else message[:ERROR_MAX_LENGTH - 1] + '…'


def parseSyncLogs(entries: list, now: int, windowDays: int = WINDOW_DAYS) -> list:
    """Group MISP log entries by sync server: one item per remote, with its `pull` and `push` activity (None for a
    direction without any run in the window). Remotes are ordered by id"""
    since = now - windowDays * DAY
    remotes = {}
    for entry in entries:
        log = entry.get('Log', entry) if isinstance(entry, dict) else None
        if not isinstance(log, dict):
            continue
        title = TITLE_RE.match(log.get('title') or '')
        created = _parseCreated(log.get('created'))
        try:
            remoteID = int(log.get('model_id'))
        except (TypeError, ValueError):
            continue
        if title is None or created is None or not (since <= created <= now):
            continue
        kind = title.group('kind')
        direction = 'pull' if kind in ('Pull from', 'Failed pull from') else 'push'
        failed = kind.startswith('Failed')
        if not failed:
            counts = parsePullChange(log.get('change')) if direction == 'pull' else parsePushChange(log.get('change'))
            if counts is None:
                continue
        remote = remotes.setdefault(remoteID, {'remote_server_id': remoteID, 'url': title.group('url'), 'pull': None, 'push': None})
        activity = remote[direction]
        if activity is None:
            counters = PULL_COUNTERS + ('events_failed',) if direction == 'pull' else ('events', 'events_failed', 'collections')
            activity = remote[direction] = _emptyDirection(counters, windowDays)
        bucket = activity['daily'][min(windowDays - 1, (created - since) // DAY)]
        activity['runs'] += 1
        bucket['runs'] += 1
        if activity['last_run'] is None or created >= activity['last_run']:
            activity['last_run'] = created
            remote['url'] = title.group('url')
        if failed:
            activity['failures'] += 1
            bucket['failures'] += 1
            if activity['last_failure'] is None or created >= activity['last_failure']:
                activity['last_failure'] = created
                activity['last_error'] = _failureMessage(kind, log.get('change'))
        else:
            for counter, value in counts.items():
                activity['totals'][counter] += value
            bucket['events'] += counts['events']
            if activity['last_success'] is None or created >= activity['last_success']:
                activity['last_success'] = created
    return [remotes[remoteID] for remoteID in sorted(remotes)]


def readableLogError(answer: dict) -> str:
    status = answer.get('_status_code')
    if status in (403, 405):
        return "MISP refused to list its logs: the API key needs admin rights"
    if status == 404:
        return "This MISP cannot search its logs through the API"
    error = answer.get('error') or answer.get('message') or answer.get('name')
    if isinstance(error, str) and error.startswith('Exception'):
        return 'Unexpected answer from MISP'
    return error or f"MISP answered with HTTP {status}"


def fetchSyncLogs(server, windowDays: int) -> dict:
    """{'entries': [...]} or {'error': message}"""
    answer = mispPostRequest(server, '/admin/logs/index', {
        'model': 'Server',
        'title': TITLE_FILTERS,
        'created': f'{windowDays}d',
        'limit': MAX_ENTRIES,
    }, timeout=REQUEST_TIMEOUT)
    if not isinstance(answer, dict):
        return {'error': 'Unexpected answer from MISP'}
    if 'error' in answer or (answer.get('_status_code') or 200) >= 400 or not isinstance(answer.get('data'), list):
        return {'error': readableLogError(answer)}
    return {'entries': answer['data']}


def collectSyncActivity(server, now: Optional[int] = None) -> dict:
    now = int(time.time()) if now is None else now
    windowDays = WINDOW_DAYS
    fetched = fetchSyncLogs(server, windowDays)
    truncated = False
    if 'entries' in fetched and len(fetched['entries']) >= MAX_ENTRIES:
        windowDays = 1
        fetched = fetchSyncLogs(server, windowDays)
        truncated = 'entries' in fetched and len(fetched['entries']) >= MAX_ENTRIES
    if 'error' in fetched:
        return {'server_id': server.id, 'timestamp': now, 'error': fetched['error']}
    return {
        'server_id': server.id,
        'timestamp': now,
        'window_days': windowDays,
        'truncated': truncated,
        'remotes': parseSyncLogs(fetched['entries'], now, windowDays),
    }


def getSyncActivity(server, refresh: bool = False) -> dict:
    """The server's sync activity, cached for 10 minutes: the log search can be slow on a busy MISP. Errors are not
    cached, so the next look tries again"""
    key = f"{KEY_SYNC_ACTIVITY}:{server.id}"
    if not refresh:
        cached = redisClient.get(key)
        if cached is not None:
            activity = json.loads(cached)
            activity['cached'] = True
            return activity
    activity = collectSyncActivity(server)
    if 'error' not in activity:
        redisClient.set(key, json.dumps(activity), ex=CACHE_SECONDS)
    activity['cached'] = False
    return activity
