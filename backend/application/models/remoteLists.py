#!/usr/bin/env python3
"""Lists read live from MISP servers for their Remote administration tabs (organisations, sharing groups): kept a few
minutes per server, and gathered for the other servers of a fleet to compare with"""

import asyncio
import json
import time
from typing import Callable, Dict, Iterable, List, Optional, Sequence

import application.models.mispOps as mispOps
from application.DBModels import Server
from application.redisModel import redisClient

CACHE_SECONDS = 10 * 60
# Comparing with the rest of the fleet: servers listed at the same time, and how long each may take
FLEET_CONCURRENCY = 25
FLEET_TIMEOUT = 30


class RemoteListError(Exception):
    """A request the tab cannot carry out: `status` is the HTTP status to answer, `field` the input at fault"""

    def __init__(self, message: str, status: int = 400, field: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.field = field


class ListCache:
    """`<prefix>:<server uuid>` → `{fetched_at, <field>: [...]}`. Failures are never stored"""

    def __init__(self, prefix: str, field: str, seconds: int = CACHE_SECONDS):
        self.prefix = prefix
        self.field = field
        self.seconds = seconds

    def key(self, server: Server) -> str:
        return f'{self.prefix}:{server.uuid}'

    def read(self, server: Server) -> Optional[dict]:
        raw = redisClient.get(self.key(server))
        if raw is None:
            return None
        try:
            cached = json.loads(raw)
        except ValueError:
            return None
        return cached if isinstance(cached, dict) and isinstance(cached.get(self.field), list) else None

    def store(self, server: Server, items: List[dict], now: Optional[int] = None) -> dict:
        listed = {'fetched_at': int(now if now is not None else time.time()), self.field: items}
        redisClient.set(self.key(server), json.dumps(listed), ex=self.seconds)
        return listed

    def forget(self, servers: Iterable[Server]) -> None:
        keys = [self.key(server) for server in servers]
        if keys:
            redisClient.delete(*keys)


def fleetServers(server: Server) -> List[Server]:
    """The other servers of the server's fleet, by name"""
    servers = Server.query.filter(Server.fleet_id == server.fleet_id, Server.user_id == server.user_id,
                                  Server.id != server.id).all()
    return sorted(servers, key=lambda other: (other.name.lower(), other.id))


async def fetchLists(servers: List[Server], urls: Sequence[str], decode: Callable[[list], List[dict]],
                     cache: ListCache, what: str, concurrency: int = FLEET_CONCURRENCY,
                     timeout: int = FLEET_TIMEOUT) -> Dict[int, object]:
    """server ID → its stored list (`{fetched_at, <field>}`), or the reason it could not be read. `decode` turns the
    decoded answers of `urls` (in order) into the list, raising MispOpError when one is a failure"""
    from application.models.utils import asyncFetcher
    semaphore = asyncio.Semaphore(max(int(concurrency), 1))

    async def fetch(server):
        async with semaphore:
            try:
                answers = await asyncFetcher(server, list(urls), timeout=timeout)
                return server.id, cache.store(server, decode(answers))
            except mispOps.MispOpError as e:
                # Shown as "could not be listed: <reason>"
                return server.id, e.message.replace(f'Could not list the {what}: ', '', 1)
            except Exception as e:
                return server.id, f'Unexpected error: {e}'
    return dict(await asyncio.gather(*[fetch(server) for server in servers]))


def gatherFleet(server: Server, cache: ListCache, urls: Sequence[str], decode: Callable[[list], List[dict]],
                what: str, refresh: bool = False, timeout: int = FLEET_TIMEOUT) -> dict:
    """The lists of the other servers of the server's fleet: from the cache when fresh, else read now, concurrently.
    `{compared: [{id, name, fetched_at}], unavailable: [{id, name, error}], lists: {server id: [...]}}`. A server
    whose list could not be read is `unavailable`, never counted as missing an item"""
    lists, unavailable, todo = {}, [], []
    others = fleetServers(server)
    for other in others:
        cached = None if refresh else cache.read(other)
        if cached is not None:
            lists[other.id] = cached
        elif not other.authkey:
            unavailable.append({'id': other.id, 'name': other.name, 'error': 'No API key'})
        else:
            todo.append(other)
    if todo:
        fetched = asyncio.run(fetchLists(todo, urls, decode, cache, what, timeout=timeout))
        for server_id, outcome in fetched.items():
            if isinstance(outcome, dict):
                lists[server_id] = outcome
            else:
                other = next(candidate for candidate in todo if candidate.id == server_id)
                unavailable.append({'id': other.id, 'name': other.name, 'error': outcome})
    unavailable.sort(key=lambda entry: (entry['name'].lower(), entry['id']))
    return {
        'compared': [{'id': other.id, 'name': other.name, 'fetched_at': lists[other.id]['fetched_at']}
                     for other in others if other.id in lists],
        'unavailable': unavailable,
        'lists': {server_id: listed[cache.field] for server_id, listed in lists.items()},
    }
