#!/usr/bin/env python3
"""Which organisations each server has (UUID → name), kept from every listing of them, and how they line up across a
fleet: what the `organisation_mismatch` health rule reads.

A server's digest is replaced each time its organisations are listed (full refresh, Organisations tab, fleet
comparison, copy) and expires after `DIGEST_SECONDS`: a server not listed for that long stops counting. The findings
of a fleet are computed from the digests of its servers and kept with the signature of each digest used, so they are
computed again only when one of them changes.

Per organisation of a server, for each other server where it does not line up:
- `renamed`: the same UUID under another name there;
- `split_there`: the same UUID under another name there, and another organisation there holds our name. MISP's
  capture creates `name_<random>` when sync brings an unknown UUID whose name is taken: the same organisation twice;
- `split_here`: the same UUID under another name there, and that name is another organisation here (the same
  situation, seen from the other side);
- `other_uuid`: not there, but an organisation of the same name is, with another UUID.
Names are compared case-insensitively, with runs of whitespace collapsed (as the Organisations tab compares them).
"""

import hashlib
import json
import time
from typing import Dict, Iterable, List, Optional

from application.redisModel import KEY_FLEET_ORG_FINDINGS, KEY_SERVER_ORG_DIGEST, redisClient

DIGEST_SECONDS = 2 * 24 * 3600
KINDS = ('other_uuid', 'split_there', 'split_here', 'renamed')


def normalisedName(name: str) -> str:
    """Names compared across servers: case and runs of whitespace do not matter"""
    return ' '.join(str(name or '').split()).lower()


def digestKey(server) -> str:
    return f'{KEY_SERVER_ORG_DIGEST}:{server.uuid}'


def findingsKey(fleet_id: int) -> str:
    return f'{KEY_FLEET_ORG_FINDINGS}:{fleet_id}'


def signature(names: Dict[str, str]) -> str:
    return hashlib.sha1(json.dumps(sorted(names.items())).encode()).hexdigest()


# Digests

def remember(server, organisations: Iterable[dict], now: Optional[int] = None, publish_self: bool = True) -> bool:
    """Keep the organisations just listed for the server (records with `uuid` and `name`). When they differ from the
    previous listing, the fleet's findings are computed again and the servers whose findings changed get their health
    published (the server itself only with `publish_self`). Returns whether the digest changed. Never raises: a
    listing must not fail because of it"""
    try:
        names = {org['uuid']: org.get('name') or '' for org in organisations if org.get('uuid')}
        sig = signature(names)
        key = digestKey(server)
        fetchedAt = int(now if now is not None else time.time())
        previous = redisClient.hget(key, 'sig')
        pipe = redisClient.pipeline()
        if previous == sig:
            pipe.hset(key, 'fetched_at', fetchedAt)
        else:
            pipe.hset(key, mapping={'sig': sig, 'fetched_at': fetchedAt, 'names': json.dumps(names)})
        pipe.expire(key, DIGEST_SECONDS)
        pipe.execute()
    except Exception as e:
        print(f"Could not keep the organisations of server {getattr(server, 'id', server)}: {e}")
        return False
    if previous != sig:
        fleetChanged(server, publish_self=publish_self)
    return previous != sig


def readDigest(server) -> Optional[dict]:
    """`{sig, fetched_at, names}` or None"""
    raw = redisClient.hgetall(digestKey(server))
    if not raw or 'names' not in raw:
        return None
    try:
        names = json.loads(raw['names'])
    except ValueError:
        return None
    return {'sig': raw.get('sig'), 'fetched_at': int(raw.get('fetched_at') or 0), 'names': names}


def hasDigest(server) -> bool:
    return bool(redisClient.hexists(digestKey(server), 'sig'))


# Findings

def computeFindings(digests: Dict[int, Dict[str, str]]) -> Dict[int, Dict[str, dict]]:
    """server ID → {organisation UUID: {name, <kind>: [...]}} for the organisations that do not line up somewhere.
    `renamed`: `[server_id, their name]`; `split_there`: `[server_id, their name, UUID of the one named like ours
    there]`; `split_here`: `[server_id, their name, UUID of the one named like theirs here]`; `other_uuid`:
    `[server_id, their UUID]`. Only organisations whose UUID has several names in the fleet, or whose name has
    several UUIDs, are looked at server by server: a fleet that lines up costs one pass"""
    order = sorted(digests)
    namesOfUuid = {}  # uuid → normalised names it has in the fleet
    uuidsOfName = {}  # normalised name → uuids it has in the fleet
    holders = {}  # server id → {normalised name: uuid}, the first by UUID when a server has the name twice
    for server_id in order:
        own = holders[server_id] = {}
        for uuid in sorted(digests[server_id]):
            name = normalisedName(digests[server_id][uuid])
            namesOfUuid.setdefault(uuid, set()).add(name)
            uuidsOfName.setdefault(name, set()).add(uuid)
            own.setdefault(name, uuid)
    findings = {}
    for server_id in order:
        for uuid, ourName in digests[server_id].items():
            name = normalisedName(ourName)
            if len(namesOfUuid[uuid]) < 2 and len(uuidsOfName[name]) < 2:
                continue
            entry = {kind: [] for kind in KINDS}
            for other in order:
                if other == server_id:
                    continue
                theirName = digests[other].get(uuid)
                holderThere = holders[other].get(name)
                if theirName is None:
                    if holderThere is not None:
                        entry['other_uuid'].append([other, holderThere])
                    continue
                theirs = normalisedName(theirName)
                if theirs == name:
                    continue
                holderHere = holders[server_id].get(theirs)
                if holderThere is not None and holderThere != uuid:
                    entry['split_there'].append([other, theirName, holderThere])
                elif holderHere is not None and holderHere != uuid:
                    entry['split_here'].append([other, theirName, holderHere])
                else:
                    entry['renamed'].append([other, theirName])
            if any(entry.values()):
                findings.setdefault(server_id, {})[uuid] = {'name': ourName, **entry}
    return findings


def fleetServers(fleet_id: int, user_id: Optional[int] = None) -> List:
    from application.DBModels import Server
    query = Server.query.filter(Server.fleet_id == fleet_id)
    if user_id is not None:
        query = query.filter(Server.user_id == user_id)
    return query.all()


def currentSignatures(servers: List) -> Dict[str, str]:
    """server ID (as text) → the signature of its digest, for the servers that have one"""
    if not servers:
        return {}
    pipe = redisClient.pipeline()
    for server in servers:
        pipe.hget(digestKey(server), 'sig')
    return {str(server.id): sig for server, sig in zip(servers, pipe.execute()) if sig}


def storedFindings(fleet_id: int) -> Optional[dict]:
    raw = redisClient.get(findingsKey(fleet_id))
    if raw is None:
        return None
    try:
        stored = json.loads(raw)
    except ValueError:
        return None
    return stored if isinstance(stored, dict) and isinstance(stored.get('findings'), dict) else None


def fleetFindings(fleet_id: int, user_id: Optional[int] = None) -> dict:
    """`{servers: {id: name}, compared: [ids], findings: {server id: {uuid: …}}}` (integer server IDs). Reuses the
    stored findings while every digest they were computed from is unchanged"""
    servers = fleetServers(fleet_id, user_id)
    names = {server.id: server.name for server in servers}
    sigs = currentSignatures(servers)
    stored = storedFindings(fleet_id)
    if stored is None or stored.get('sigs') != sigs:
        stored = computeAndStore(fleet_id, servers, sigs)
    return {
        'servers': names,
        'compared': sorted(int(server_id) for server_id in stored['sigs']),
        'findings': {int(server_id): found for server_id, found in stored['findings'].items()},
    }


def computeAndStore(fleet_id: int, servers: List, sigs: Dict[str, str]) -> dict:
    digests, used = {}, {}
    for server in servers:
        if str(server.id) not in sigs:
            continue
        digest = readDigest(server)
        if digest is None:
            continue
        digests[server.id] = digest['names']
        used[str(server.id)] = digest['sig']
    findings = computeFindings(digests) if len(digests) > 1 else {}
    stored = {'sigs': used, 'findings': {str(server_id): found for server_id, found in findings.items()}}
    redisClient.set(findingsKey(fleet_id), json.dumps(stored), ex=DIGEST_SECONDS)
    return stored


def fleetChanged(server, publish_self: bool = True) -> None:
    """A digest of the fleet changed: compute the findings again and publish the health of the servers whose
    findings changed. Never raises"""
    fleet_id = getattr(server, 'fleet_id', None)
    if fleet_id is None:
        return
    try:
        before = (storedFindings(fleet_id) or {}).get('findings', {})
        servers = fleetServers(fleet_id, getattr(server, 'user_id', None))
        after = computeAndStore(fleet_id, servers, currentSignatures(servers))['findings']
    except Exception as e:
        print(f'Could not compare the organisations of fleet {fleet_id}: {e}')
        return
    changed = {int(server_id) for server_id in set(before) | set(after)
               if before.get(server_id) != after.get(server_id)}
    if not publish_self:
        changed.discard(server.id)
    if not changed:
        return
    from application.models.health import publishServerHealth
    for other in servers:
        if other.id in changed:
            publishServerHealth(other)
