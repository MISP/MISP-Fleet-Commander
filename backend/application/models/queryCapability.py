"""Whether a server runs complex queries (MispQL's WHERE), told by what it answers and never by its version

A MISP without them drops a search's `query` without a word and answers as if there were no WHERE: unrelated rows
presented as matches, every event counted. So a server counts as `supported` only once its answer to
`GET /attributes/queryDescribe` lists its tables. That answer is cached here for the UI (server picker, field
completion) and forgotten when the server is refreshed, edited or deleted. Whatever sends a query asks again right
before sending: mispql's `Exchange` does by default.

The snapshot's Role never makes a server supported: a web server's stale schema cache hides its `perm_complex_query`,
and a migrated database behind older code shows it while dropping `query`. It only tells a missing permission apart
from the other 403s.
"""
import json
import time
from typing import Optional

import mispql

from application import redisModel
from application.controllers.utils import mispRawRequest

SUPPORTED = 'supported'
NOT_SUPPORTED = 'not_supported'  # 404: this MISP has no complex queries
NO_PERMISSION = 'no_permission'  # 403, and the key's role has Complex query off and is not a site admin's
UNAVAILABLE = 'unavailable'  # 403 otherwise: no permission, or a MISP without them refusing an action it doesn't know
UNREACHABLE = 'unreachable'  # no answer
UNKNOWN = 'unknown'  # any other answer

CACHE_SECONDS = 3600
# Unreachable or unknown: asked again soon, rather than hiding the server from queries for an hour
RETRY_SECONDS = 60


def classify(status: int, body, role: Optional[dict] = None) -> dict:
    """The capability shown by a server's answer to `mispql.SUPPORT_CHECK`. `role` is the key's Role from the server's
    snapshot, used only to tell a missing permission apart from the other 403s"""
    try:
        mispql.check_support(status, body)
    except mispql.NoComplexQueries as e:
        if e.status == 404:
            state = NOT_SUPPORTED
        elif e.status == 403:
            state = NO_PERMISSION if lacksPermission(role) else UNAVAILABLE
        else:
            state = UNKNOWN
        return capability(state, e.status, str(e))
    return capability(SUPPORTED, status, '')


def lacksPermission(role: Optional[dict]) -> bool:
    """The role says outright that it may not run complex queries: its Complex query permission is there and off, and
    it is not a site admin's. A role without that field (an older MISP, a stale schema cache) says nothing"""
    if not isinstance(role, dict) or 'perm_complex_query' not in role:
        return False
    return not isOn(role.get('perm_complex_query')) and not isOn(role.get('perm_site_admin'))


def isOn(flag) -> bool:
    return flag in (True, 1, '1', 'true')


def snapshotRole(server) -> Optional[dict]:
    """The key's Role as the server's last snapshot recorded it (`/users/view/me`), or None"""
    info = redisModel.getServerInfo(server.uuid) or {}
    user = (info.get('query_result') or {}).get('serverUser')
    role = user.get('Role') if isinstance(user, dict) else None
    return role if isinstance(role, dict) else None


def check(server) -> dict:
    """Asks the server now, never from a cache, and keeps its answer for the UI"""
    response = mispRawRequest(server, mispql.SUPPORT_CHECK.method, mispql.SUPPORT_CHECK.path)
    if isinstance(response, dict):
        found = capability(UNREACHABLE, None, response.get('error') or 'No answer')
    else:
        found = classify(response.status_code, response.content, snapshotRole(server))
    seconds = RETRY_SECONDS if found['state'] in (UNREACHABLE, UNKNOWN) else CACHE_SECONDS
    redisModel.redisClient.set(cacheKey(server.id), json.dumps(found), ex=seconds)
    return found


def get(server, refresh: bool = False) -> dict:
    """The server's capability: the cached one, else (or with `refresh`) asked now"""
    if not refresh:
        cached = redisModel.redisClient.get(cacheKey(server.id))
        if cached:
            try:
                return {**json.loads(cached), 'cached': True}
            except (ValueError, TypeError):
                pass
    return check(server)


def forget(server_id: int) -> None:
    redisModel.redisClient.delete(cacheKey(server_id))


def cacheKey(server_id: int) -> str:
    return f'{redisModel.KEY_QUERY_CAPABILITY}:{server_id}'


def capability(state: str, status: Optional[int], detail: str) -> dict:
    return {'state': state, 'status': status, 'detail': detail, 'checked_at': int(time.time())}
