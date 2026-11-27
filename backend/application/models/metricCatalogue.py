"""The usage metrics collected from each MISP server: what they are, which request they come from and how its answer
is read. The collector, the roll-ups, the API and the Prometheus endpoint all work from this list.

The kind of a metric says how it sums up over an hour or a day:
- `total`: a running count (events, users). A bucket keeps its last value.
- `gauge`: a level that goes up and down (load, memory, queues). A bucket keeps the average and the maximum.
- `delta`: what happened since the previous collection (logins). A bucket keeps the sum.

Parsers take the answer of a request helper (`mispGetRequest` / `mispPostRequest`) and return the values they could
read. They raise `UnreadableAnswer` when the answer has none of them. Nothing that identifies a person (the API key
owner's email in the system widget, the keys and emails of the API activity widget, the users of the log entries)
is ever returned.

What Fleet Commander does on a server is not usage: the API requests and the logins of its own account (the owner of
its API key, `OwnAccount`) are left out. That account is read on each collection and kept nowhere.
"""
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

TOTAL, GAUGE, DELTA = 'total', 'gauge', 'delta'
KINDS = (TOTAL, GAUGE, DELTA)

CONTENT, COMMUNITY, ACTIVITY, SYSTEM, INTERNALS = 'content', 'community', 'activity', 'system', 'internals'
GROUPS = (CONTENT, COMMUNITY, ACTIVITY, SYSTEM, INTERNALS)


@dataclass(frozen=True)
class Metric:
    key: str
    group: str
    kind: str
    unit: str  # count, percent, bytes, load, jobs
    source: str
    label: str


CATALOGUE = (
    Metric('events', CONTENT, TOTAL, 'count', 'statistics', 'Events'),
    Metric('attributes', CONTENT, TOTAL, 'count', 'statistics', 'Attributes'),
    Metric('objects', CONTENT, TOTAL, 'count', 'statistics', 'Objects'),
    Metric('event_reports', CONTENT, TOTAL, 'count', 'statistics', 'Event reports'),
    Metric('analyst_data', CONTENT, TOTAL, 'count', 'statistics', 'Analyst data'),
    Metric('correlations', CONTENT, TOTAL, 'count', 'statistics', 'Correlations'),
    Metric('proposals', CONTENT, TOTAL, 'count', 'statistics', 'Proposals'),
    Metric('users', COMMUNITY, TOTAL, 'count', 'statistics', 'Users'),
    Metric('users_pgp', COMMUNITY, TOTAL, 'count', 'statistics', 'Users with a PGP key'),
    Metric('orgs', COMMUNITY, TOTAL, 'count', 'statistics', 'Organisations'),
    Metric('local_orgs', COMMUNITY, TOTAL, 'count', 'statistics', 'Local organisations'),
    Metric('contributing_orgs', COMMUNITY, TOTAL, 'count', 'statistics', 'Contributing organisations'),
    Metric('pending_registrations', COMMUNITY, TOTAL, 'count', 'registrations', 'Pending registrations'),
    Metric('logins', ACTIVITY, DELTA, 'count', 'logins', 'Logins'),
    Metric('failed_logins', ACTIVITY, DELTA, 'count', 'logins', 'Failed logins'),
    Metric('api_requests_24h', ACTIVITY, GAUGE, 'count', 'api_activity',
           "API requests (last 24 hours, Fleet Commander's own left out)"),
    # The same requests by who made them: sync users (other MISP servers), keys MISP cannot tell the owner of, and
    # everyone else. Only from MISP 2.5 on, whose widget names each key's role
    Metric('api_requests_users_24h', ACTIVITY, GAUGE, 'count', 'api_activity',
           'API requests by users and tools (last 24 hours)'),
    Metric('api_requests_sync_24h', ACTIVITY, GAUGE, 'count', 'api_activity',
           'API requests by sync users (last 24 hours)'),
    Metric('api_requests_unknown_24h', ACTIVITY, GAUGE, 'count', 'api_activity',
           'API requests with unknown keys (last 24 hours)'),
    Metric('load_1', SYSTEM, GAUGE, 'load', 'system', 'Load (1 min)'),
    Metric('load_5', SYSTEM, GAUGE, 'load', 'system', 'Load (5 min)'),
    Metric('load_15', SYSTEM, GAUGE, 'load', 'system', 'Load (15 min)'),
    Metric('memory_used_pct', SYSTEM, GAUGE, 'percent', 'system', 'Memory used'),
    Metric('memory_free_bytes', SYSTEM, GAUGE, 'bytes', 'system', 'Memory free'),
    Metric('disk_used_pct', SYSTEM, GAUGE, 'percent', 'system', 'Disk used'),
    Metric('db_size_bytes', SYSTEM, GAUGE, 'bytes', 'admin', 'Database size'),
    Metric('queue_cache', INTERNALS, GAUGE, 'jobs', 'diagnostics', 'Cache queue'),
    Metric('queue_default', INTERNALS, GAUGE, 'jobs', 'diagnostics', 'Default queue'),
    Metric('queue_email', INTERNALS, GAUGE, 'jobs', 'diagnostics', 'Email queue'),
    Metric('queue_prio', INTERNALS, GAUGE, 'jobs', 'diagnostics', 'Priority queue'),
    Metric('queue_update', INTERNALS, GAUGE, 'jobs', 'diagnostics', 'Update queue'),
    Metric('redis_memory_bytes', INTERNALS, GAUGE, 'bytes', 'diagnostics', 'Redis memory'),
    Metric('redis_memory_peak_bytes', INTERNALS, GAUGE, 'bytes', 'diagnostics', 'Redis memory peak'),
)
METRICS = {metric.key: metric for metric in CATALOGUE}

# The keys that add up across the servers of a fleet. Content synced between them counts once per server holding it.
# Not summed: organisations (the same ones are known, or local, on several servers), and load, memory, disk and
# Redis, which describe one machine each
FLEET_SUMMED = frozenset((
    'events', 'attributes', 'objects', 'event_reports', 'analyst_data', 'correlations', 'proposals',
    'users', 'users_pgp', 'pending_registrations',
    'logins', 'failed_logins', 'api_requests_24h', 'api_requests_users_24h', 'api_requests_sync_24h',
    'api_requests_unknown_24h',
    'db_size_bytes', 'queue_cache', 'queue_default', 'queue_email', 'queue_prio', 'queue_update',
))


def kindOf(key: str) -> Optional[str]:
    metric = METRICS.get(key)
    return metric.kind if metric else None


class UnreadableAnswer(ValueError):
    pass


def _number(value):
    """A number MISP sent as a number or as a string"""
    if isinstance(value, bool) or value is None:
        raise ValueError('not a number')
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    return int(text) if re.fullmatch(r'-?\d+', text) else float(text)


SIZE_RE = re.compile(r'^\s*(?P<number>\d+(?:\.\d+)?)\s*(?P<unit>[KMGTP]?)(?:i?B)?\s*$', re.IGNORECASE)
SIZE_FACTORS = {'': 1, 'K': 1024, 'M': 1024 ** 2, 'G': 1024 ** 3, 'T': 1024 ** 4, 'P': 1024 ** 5}


def parseSize(text) -> Optional[int]:
    """`"8893.8M"` → bytes (MISP's sizes are binary: MB = 1024² bytes)"""
    match = SIZE_RE.match(str(text or ''))
    if match is None:
        return None
    return int(round(float(match['number']) * SIZE_FACTORS[match['unit'].upper()]))


def _rows(answer) -> list:
    """The entries of a widget answer: `mispPostRequest` wraps the list MISP returns in `{data: [...]}`"""
    rows = answer.get('data') if isinstance(answer, dict) else answer
    if not isinstance(rows, list):
        raise UnreadableAnswer('Unexpected answer')
    return [row for row in rows if isinstance(row, dict)]


STATISTICS_FIELDS = {
    'events': 'event_count',
    'attributes': 'attribute_count',
    'objects': 'object_count',
    'event_reports': 'eventreport_count',
    'analyst_data': 'analyst_data_count',
    'correlations': 'correlation_count',
    'proposals': 'proposal_count',
    'users': 'user_count',
    'users_pgp': 'user_count_pgp',
    'orgs': 'org_count',
    'local_orgs': 'local_org_count',
    'contributing_orgs': 'contributing_org_count',
}


def parseStatistics(answer) -> dict:
    """`GET /users/statistics`: `{stats: {event_count: "4291", …}}`. Older MISPs have no analyst data or reports"""
    stats = answer.get('stats') if isinstance(answer, dict) else None
    if not isinstance(stats, dict):
        raise UnreadableAnswer('No statistics in the answer')
    values = {}
    for key, field in STATISTICS_FIELDS.items():
        try:
            values[key] = int(_number(stats[field]))
        except (KeyError, TypeError, ValueError):
            continue
    if not values:
        raise UnreadableAnswer('No statistics in the answer')
    return values


def parseRegistrations(answer) -> dict:
    """`GET /users/registrations`: the list of pending registrations"""
    if isinstance(answer, dict) and isinstance(answer.get('data'), list):
        answer = answer['data']
    if not isinstance(answer, list):
        raise UnreadableAnswer('Unexpected answer')
    return {'pending_registrations': len(answer)}


QUEUES = ('cache', 'default', 'email', 'prio', 'update')


def parseDiagnostics(answer) -> dict:
    """`GET /servers/serverSettings/diagnostics/light:1`: worker queues (`workers.<queue>.jobCount`) and Redis
    memory (`redisInfo.used_memory`, `used_memory_peak`, in bytes)"""
    if not isinstance(answer, dict):
        raise UnreadableAnswer('Unexpected answer')
    values = {}
    workers = answer.get('workers')
    if isinstance(workers, dict):
        for queue in QUEUES:
            worker = workers.get(queue)
            try:
                values[f'queue_{queue}'] = int(_number(worker['jobCount']))
            except (KeyError, TypeError, ValueError):
                continue
    redisInfo = answer.get('redisInfo')
    if isinstance(redisInfo, dict):
        for key, field in (('redis_memory_bytes', 'used_memory'), ('redis_memory_peak_bytes', 'used_memory_peak')):
            try:
                values[key] = int(_number(redisInfo[field]))
            except (KeyError, TypeError, ValueError):
                continue
    if not values:
        raise UnreadableAnswer('No worker or Redis figures in the diagnostics')
    return values


MEMORY_RE = re.compile(r'^\s*(?P<free>\d+(?:\.\d+)?)\s*MB free\s*\(\s*(?P<used>\d+(?:\.\d+)?)\s*%\s*used\s*\)')
LOAD_RE = re.compile(r'^\s*(?P<l1>\d+(?:\.\d+)?)\s*-\s*(?P<l5>\d+(?:\.\d+)?)\s*-\s*(?P<l15>\d+(?:\.\d+)?)\s*$')
DISK_RE = re.compile(r'^\s*(?P<used>\d+(?:\.\d+)?)\s*%')


def parseSystemWidget(answer) -> dict:
    """`MispSystemResourceWidget`: rows `{title, value}` whose titles are translated, so the values are recognised
    by their format: `"77.27%"` (or `"91.2% - [Above Threshold]"`), `"4.16 - 4.87 - 4.63"`,
    `"3099.95 MB free (90.23 % used)"`. The other rows (the API key owner's email, the system name) are skipped"""
    values = {}
    for row in _rows(answer):
        text = str(row.get('value') if row.get('value') is not None else '')
        memory = MEMORY_RE.match(text)
        if memory:
            values['memory_free_bytes'] = int(round(float(memory['free']) * 1024 ** 2))
            values['memory_used_pct'] = float(memory['used'])
            continue
        load = LOAD_RE.match(text)
        if load:
            values['load_1'], values['load_5'], values['load_15'] = (float(load['l1']), float(load['l5']),
                                                                    float(load['l15']))
            continue
        disk = DISK_RE.match(text)
        if disk and 'disk_used_pct' not in values:
            values['disk_used_pct'] = float(disk['used'])
    if not values:
        raise UnreadableAnswer('No load, memory or disk figures in the system widget')
    return values


def parseAdminWidget(answer) -> dict:
    """`MispAdminResourceWidget`: `Current Redis memory usage` and `Peak Redis memory usage` (only when MISP reaches
    Redis), then `MySQL DB disk usage`, the size of MISP's database. Sizes look like `"8893.8M"`. Titles are
    translated, so the rows are read by position (the same from MISP 2.4 to 3.0); the English titles are only used
    if the widget ever has another layout"""
    rows = _rows(answer)
    sizes = [parseSize(row.get('value')) for row in rows]
    if len(rows) == 3 and None not in sizes:
        return {'redis_memory_bytes': sizes[0], 'redis_memory_peak_bytes': sizes[1], 'db_size_bytes': sizes[2]}
    if len(rows) == 1 and sizes[0] is not None:
        return {'db_size_bytes': sizes[0]}
    values = {}
    for row, size in zip(rows, sizes):
        title = str(row.get('title') or '').lower()
        if size is None:
            continue
        if 'mysql' in title:
            values['db_size_bytes'] = size
        elif 'redis' in title and 'peak' in title:
            values['redis_memory_peak_bytes'] = size
        elif 'redis' in title:
            values['redis_memory_bytes'] = size
    if not values:
        raise UnreadableAnswer('No size in the admin widget')
    return values


@dataclass(frozen=True)
class OwnAccount:
    """The MISP account Fleet Commander's API key belongs to on a server. `email` is casefolded; `key` is how MISP
    counts the requests of a key: its first and last 4 characters"""
    user_id: Optional[int]
    email: str
    key: str


def keyFingerprint(authkey) -> str:
    key = str(authkey or '').strip()
    return key[:4] + key[-4:] if len(key) >= 8 else ''


def parseOwnAccount(answer, authkey) -> OwnAccount:
    """`GET /users/view/me`: `{User: {id: "16", email: …}, Role: …}`"""
    user = answer.get('User') if isinstance(answer, dict) else None
    email = str(user.get('email') or '').strip() if isinstance(user, dict) else ''
    if not email:
        raise UnreadableAnswer('No user in the answer')
    try:
        userId = int(_number(user.get('id')))
    except (TypeError, ValueError):
        userId = None
    return OwnAccount(userId, email.casefold(), keyFingerprint(authkey))


REQUESTS_RE = re.compile(r'(\d+)\s+requests?\b')
LEADING_NUMBER_RE = re.compile(r'^\s*(\d+)')
USER_LINK_RE = re.compile(r'/admin/users/view/(\d+)\b')


def _isOwnKeyRow(row: dict, own: Optional[OwnAccount]) -> bool:
    """Whether a row of the API activity widget is a key of Fleet Commander's own account. MISP 2.5 and 3 name a key
    by its owner's email, or by the key itself when MISP cannot tell its owner (an "unknown key", as legacy keys
    are). MISP 2.4 links a key to its owner (`/admin/users/view/<id>` in `html`) and shows the key in `html_title`,
    or in `title` when it is unknown"""
    if own is None:
        return False
    if 'type' in row:
        name = str(row.get('name') or '').strip()
        return name.casefold() == own.email or (bool(own.key) and name == own.key)
    owner = USER_LINK_RE.search(str(row.get('html') or ''))
    if owner is not None and own.user_id is not None and int(owner[1]) == own.user_id:
        return True
    return bool(own.key) and (str(row.get('title') or '').strip() == own.key
                              or f'>{own.key}<' in str(row.get('html_title') or ''))


def _badge(row: dict) -> int:
    try:
        return int(_number(row.get('badge')))
    except (TypeError, ValueError):
        return 0


def _flag(value) -> bool:
    return value is True or str(value).strip().lower() in ('1', 'true')


def parseSyncRoles(answer) -> frozenset:
    """`GET /roles/index` → the names (casefolded) of the roles made for syncing: allowed to sync, not admins. The
    admin role may sync too, but its users are people and their tools"""
    rows = answer.get('data') if isinstance(answer, dict) else answer
    if not isinstance(rows, list):
        raise UnreadableAnswer('Unexpected answer')
    roles = [row.get('Role', row) for row in rows if isinstance(row, dict)]
    roles = [role for role in roles if isinstance(role, dict) and str(role.get('name') or '').strip()]
    if not roles:
        raise UnreadableAnswer('No role in the answer')
    return frozenset(str(role['name']).strip().casefold() for role in roles
                     if _flag(role.get('perm_sync')) and not _flag(role.get('perm_admin'))
                     and not _flag(role.get('perm_site_admin')))


def _keyKind(row: dict, syncRoles: frozenset) -> str:
    """`unknown`, `sync` or `users`. MISP links every key it knows to its page (`drilldown`) and ends its `meta` with
    the key owner's role (`key ab01 · ORGNAME · Sync user`, empty parts left out)"""
    if not row.get('drilldown'):
        return 'unknown'
    role = str(row.get('meta') or '').split(' · ')[-1].strip().casefold()
    return 'sync' if role in syncRoles else 'users'


def needsRoles(answer, own: Optional[OwnAccount]) -> bool:
    """Whether the API activity widget lists a key whose owner's role decides how its requests are counted: a known
    key other than Fleet Commander's own, on MISP 2.5 and 3"""
    return any(row.get('type') == 'user' and row.get('drilldown') and not _isOwnKeyRow(row, own)
               for row in _rows(answer))


def parseApiActivity(answer, own: Optional[OwnAccount] = None, syncRoles: Optional[frozenset] = None) -> dict:
    """`APIActivityWidget` over one day. MISP 2.5 and 3: a `header` row (`"8 keys · 1998 requests · 6 unknown"`, or
    `"No API activity in this period."`) then one `user` row per key, its requests in `badge`. The header's total is
    used when it can be read (it is translated), else the badges are summed. Older MISPs: rows whose `html` starts
    with the key's request count. The requests of Fleet Commander's own account (`own`) are left out.

    With the names of the sync roles (`syncRoles`), MISP 2.5 and 3's requests are also split by who made them: sync
    users, keys MISP does not know the owner of, and everyone else (`api_requests_{sync,unknown,users}_24h`)"""
    rows = _rows(answer)
    typed = [row for row in rows if 'type' in row]
    if typed:
        keys = [row for row in typed if row.get('type') == 'user' and not _isOwnKeyRow(row, own)]
        ownRequests = sum(_badge(row) for row in typed if row.get('type') == 'user') - sum(map(_badge, keys))
        values = {'api_requests_24h': sum(_badge(row) for row in keys)}
        for row in typed:
            if row.get('type') == 'header':
                match = REQUESTS_RE.search(str(row.get('value') or ''))
                if match:
                    values['api_requests_24h'] = max(int(match[1]) - ownRequests, 0)
                    break
        if syncRoles is not None:
            parts = {'users': 0, 'sync': 0, 'unknown': 0}
            for row in keys:
                parts[_keyKind(row, syncRoles)] += _badge(row)
            values.update({f'api_requests_{kind}_24h': count for kind, count in parts.items()})
        return values
    total, read = 0, False
    for row in rows:
        match = LEADING_NUMBER_RE.match(str(row.get('html') or row.get('value') or ''))
        if match:
            read = True
            if not _isOwnKeyRow(row, own):
                total += int(match[1])
    if rows and not read:
        raise UnreadableAnswer('No request count in the API activity widget')
    return {'api_requests_24h': total}


WIDGET_URL = '/dashboards/renderWidget/0/exportjson:1'


@dataclass(frozen=True)
class Source:
    """`per_key`: the answer counts requests per API key. The parser also takes Fleet Commander's own account, whose
    requests it leaves out, and the names of the sync roles, to split the rest (`parse(answer, own, syncRoles)`)"""
    name: str
    label: str
    method: str
    url: str
    parse: Callable[..., dict]
    payload: Optional[dict] = None
    per_key: bool = False


# Requested in this order. Statistics come first: a server that does not answer them gets no other request. When
# two sources give the same key, the first one wins (Redis memory: exact in the diagnostics, rounded in the widget)
SOURCES = (
    Source('statistics', 'Statistics', 'GET', '/users/statistics', parseStatistics),
    Source('registrations', 'Registrations', 'GET', '/users/registrations', parseRegistrations),
    Source('diagnostics', 'Diagnostics', 'GET', '/servers/serverSettings/diagnostics/light:1', parseDiagnostics),
    Source('system', 'System widget', 'POST', WIDGET_URL, parseSystemWidget,
           {'config': '{}', 'widget': 'MispSystemResourceWidget'}),
    Source('admin', 'Admin widget', 'POST', WIDGET_URL, parseAdminWidget,
           {'config': '{}', 'widget': 'MispAdminResourceWidget'}),
    Source('api_activity', 'API activity widget', 'POST', WIDGET_URL, parseApiActivity,
           {'config': json.dumps({'days': 1}), 'widget': 'APIActivityWidget'}, per_key=True),
)
OWN_ACCOUNT_URL = '/users/view/me'
ROLES_URL = '/roles/index'

# Web logins. `login_fail` is a failed one (wrong password or OTP, unknown account). `auth_fail` is not counted: it
# is an API request with a wrong, expired or disabled key, not a login
LOGIN_ACTIONS = {'login': 'logins', 'login_fail': 'failed_logins'}


@dataclass(frozen=True)
class LoginEntry:
    id: int
    key: str  # logins | failed_logins
    created: Optional[int]  # UNIX seconds, reading MISP's time as UTC


def parseLogCreated(created) -> Optional[int]:
    """MISP stores log times in its own timezone, which its API does not tell: they are read as UTC (the default of
    MISP's Docker images). A wrong guess only shifts the hours of the logins counted by the first collection"""
    try:
        return int(datetime.strptime(str(created), '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp())
    except ValueError:
        return None


def _isOwnLogin(log: dict, own: Optional[OwnAccount]) -> bool:
    """A web login with Fleet Commander's own account. Failed attempts on it are not: they may well be an attack"""
    if own is None or log.get('action') != 'login':
        return False
    try:
        if own.user_id is not None and int(_number(log.get('user_id'))) == own.user_id:
            return True
    except (TypeError, ValueError):
        pass
    return str(log.get('email') or '').strip().casefold() == own.email


def parseLoginLogs(answer, own: Optional[OwnAccount] = None) -> list:
    """`POST /admin/logs/index` → the login and failed-login entries, as LoginEntry. Entries come as `{Log: {…}}`
    (or bare), ids as strings; anything else is skipped, as are the logins of Fleet Commander's own account (`own`)"""
    entries = []
    for row in _rows(answer):
        log = row.get('Log', row)
        if not isinstance(log, dict) or log.get('action') not in LOGIN_ACTIONS or _isOwnLogin(log, own):
            continue
        try:
            logId = int(_number(log.get('id')))
        except (TypeError, ValueError):
            continue
        entries.append(LoginEntry(logId, LOGIN_ACTIONS[log['action']], parseLogCreated(log.get('created'))))
    return entries
