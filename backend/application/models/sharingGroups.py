#!/usr/bin/env python3
"""The sharing groups of a MISP server, as its Remote administration tab shows them: listed live from MISP and kept a
few minutes, compared with the other servers of its fleet, created, edited and deleted, and created or completed on
other servers of the fleet"""

import uuid as uuidLib
from typing import Callable, Dict, List, Optional, Tuple

import application.models.mispOps as mispOps
import application.models.organisations as organisationModel
from application.DBModels import Job, Server
from application.models.jobs import UnitResult
from application.models.remoteLists import FLEET_TIMEOUT, ListCache, RemoteListError, gatherFleet
from application.redisModel import KEY_SERVER_SHARING_GROUPS

LOCAL_INSTANCE = mispOps.LOCAL_INSTANCE
LOCAL_INSTANCE_NAME = 'Local instance'
MAX_NAME_LENGTH = 255
MAX_TEXT_LENGTH = 65535
MAX_MEMBERS = 2000
MAX_SERVERS = 500
ATTRIBUTES = ('name', 'description', 'releasability', 'active', 'roaming')
REQUEST_FIELDS = ATTRIBUTES + ('uuid', 'members', 'servers')
UUID_RE = organisationModel.UUID_RE
normalisedName = organisationModel.normalisedName


class SharingGroupError(RemoteListError):
    pass


# Records

def compactMember(row) -> Optional[dict]:
    org = row.get('Organisation') if isinstance(row, dict) else None
    if not isinstance(org, dict) or not org.get('uuid'):
        return None
    return {'id': mispOps.number(org.get('id') or row.get('org_id')), 'uuid': mispOps.uuidKey(org['uuid']),
            'name': mispOps.text(org.get('name')), 'extend': mispOps.flag(row.get('extend'))}


def compactServer(row) -> Optional[dict]:
    """The index names remote servers (`Server {id, name}`); the "Local instance" row has `server_id` 0 and no
    `Server`"""
    if not isinstance(row, dict):
        return None
    server = row.get('Server') if isinstance(row.get('Server'), dict) else {}
    serverId = mispOps.number(row.get('server_id', server.get('id')))
    name = LOCAL_INSTANCE_NAME if serverId == LOCAL_INSTANCE else \
        (mispOps.text(server.get('name')) or f'Server #{serverId}')
    return {'server_id': serverId, 'name': name, 'all_orgs': mispOps.flag(row.get('all_orgs'))}


def compact(entry) -> Optional[dict]:
    """What the tab needs of a sharing group index entry. MISP may hold a member or server row twice: each is listed
    once"""
    group = entry.get('SharingGroup') if isinstance(entry, dict) else None
    if not isinstance(group, dict) or not group.get('uuid'):
        return None
    creator = entry.get('Organisation') if isinstance(entry.get('Organisation'), dict) else {}
    members = {}
    for row in entry.get('SharingGroupOrg') or []:
        member = compactMember(row)
        if member is not None:
            members.setdefault(member['uuid'], member)
    servers = {}
    for row in entry.get('SharingGroupServer') or []:
        server = compactServer(row)
        if server is None:
            continue
        known = servers.setdefault(server['server_id'], server)
        known['all_orgs'] = known['all_orgs'] or server['all_orgs']
    return {
        'id': mispOps.number(group.get('id')),
        'uuid': mispOps.uuidKey(group['uuid']),
        'name': mispOps.text(group.get('name')),
        'description': mispOps.text(group.get('description')),
        'releasability': mispOps.text(group.get('releasability')),
        'active': mispOps.flag(group.get('active')),
        'roaming': mispOps.flag(group.get('roaming')),
        # Created on this instance through its own form; else received by sync or created through the API
        'local': mispOps.flag(group.get('local')),
        'creator': {'id': mispOps.number(creator.get('id')), 'uuid': mispOps.uuidKey(creator['uuid']),
                    'name': mispOps.text(creator.get('name'))} if creator.get('uuid') else None,
        'members': sorted(members.values(), key=lambda member: (member['name'].lower(), member['uuid'])),
        'servers': sorted(servers.values(), key=lambda server: (server['server_id'] != LOCAL_INSTANCE,
                                                                 server['name'].lower(), server['server_id'])),
        'editable': mispOps.flag(entry.get('editable')),
        'deletable': mispOps.flag(entry.get('deletable')),
    }


def parse(entries) -> List[dict]:
    """Sorted by name; a group listed by both indexes is kept once"""
    groups = {}
    for entry in entries:
        group = compact(entry)
        if group is not None:
            groups.setdefault(group['uuid'], group)
    return sorted(groups.values(), key=lambda group: (group['name'].lower(), group['uuid']))


# Cache

CACHE = ListCache(KEY_SERVER_SHARING_GROUPS, 'sharing_groups')
readCached = CACHE.read
store = CACHE.store
forget = CACHE.forget


def listFromMisp(server: Server) -> List[dict]:
    entries = mispOps.sharingGroupEntries(server)
    try:
        entries += mispOps.sharingGroupEntries(server, mispOps.SHARING_GROUP_PASSIVE_INDEX)
    except mispOps.MispOpError:
        pass  # Only older MISPs need it, for their inactive groups
    return parse(entries)


def sharingGroupsOf(server: Server, refresh: bool = False) -> dict:
    """`{fetched_at, cached, sharing_groups}`. Raises MispOpError when MISP cannot list them (failures are not
    cached)"""
    if not refresh:
        cached = readCached(server)
        if cached is not None:
            return {**cached, 'cached': True}
    return {**store(server, listFromMisp(server)), 'cached': False}


def findGroup(groups: List[dict], uuid: str) -> Optional[dict]:
    return next((group for group in groups if group['uuid'] == uuid), None)


def eventCount(server: Server, groupId: int) -> Optional[int]:
    """Events whose distribution is the group (not attributes, objects or reports of other events)"""
    return mispOps.eventCount(server, {'sharinggroup': int(groupId)})


# Comparison with the other servers of the fleet

def decodeList(answers: list) -> List[dict]:
    """Another client's decoded answers of both indexes. The second one may fail on its own"""
    entries = mispOps.decodedSharingGroupEntries(answers[0])
    if len(answers) > 1:
        try:
            entries += mispOps.decodedSharingGroupEntries(answers[1])
        except mispOps.MispOpError:
            pass
    return parse(entries)


def differences(ours: dict, theirs: dict) -> dict:
    """What differs on another server, with its values: `name`, `active`, `roaming`, `members_missing` (UUIDs of our
    members it lacks), `members_extra` (`[uuid, name]` of its members we lack). Extend flags and server lists are
    each instance's own rights and sync settings, so they are not compared"""
    found = {}
    if normalisedName(theirs['name']) != normalisedName(ours['name']):
        found['name'] = theirs['name']
    for field in ('active', 'roaming'):
        if theirs[field] != ours[field]:
            found[field] = theirs[field]
    mine = {member['uuid'] for member in ours['members']}
    others = {member['uuid'] for member in theirs['members']}
    missing = [member['uuid'] for member in ours['members'] if member['uuid'] not in others]
    extra = [[member['uuid'], member['name']] for member in theirs['members'] if member['uuid'] not in mine]
    if missing:
        found['members_missing'] = missing
    if extra:
        found['members_extra'] = extra
    return found


def compare(own: List[dict], others: Dict[int, List[dict]]) -> Dict[str, dict]:
    """For each group of `own` (by UUID), the other servers where it is: `same`, `differs` (`[{server_id, …what
    differs}]`), `other_uuid` (no such UUID, but a group with the same name: `[server_id, its UUID]`). Compared
    servers missing from all three do not have it"""
    indexes = {}
    for server_id, groups in others.items():
        byName = {}
        for group in groups:
            byName.setdefault(normalisedName(group['name']), group)
        indexes[server_id] = ({group['uuid']: group for group in groups}, byName)
    result = {}
    for group in own:
        entry = {'same': [], 'differs': [], 'other_uuid': []}
        for server_id, (byUuid, byName) in indexes.items():
            theirs = byUuid.get(group['uuid'])
            if theirs is not None:
                found = differences(group, theirs)
                if found:
                    entry['differs'].append({'server_id': server_id, **found})
                else:
                    entry['same'].append(server_id)
            elif normalisedName(group['name']) in byName:
                entry['other_uuid'].append([server_id, byName[normalisedName(group['name'])]['uuid']])
        result[group['uuid']] = entry
    return result


def fleetComparison(server: Server, refresh: bool = False) -> dict:
    """How the server's sharing groups compare with the rest of its fleet (see `organisations.fleetComparison`)"""
    own = sharingGroupsOf(server, refresh=refresh)['sharing_groups']
    urls = [mispOps.SHARING_GROUP_INDEX[0], mispOps.SHARING_GROUP_PASSIVE_INDEX]
    fleet = gatherFleet(server, CACHE, urls, decodeList, mispOps.SHARING_GROUP_INDEX[2], refresh=refresh,
                        timeout=FLEET_TIMEOUT)
    return {
        'server_id': server.id,
        'fleet_id': server.fleet_id,
        'compared': fleet['compared'],
        'unavailable': fleet['unavailable'],
        'sharing_groups': compare(own, fleet['lists']),
    }


# Request checks

def cleanText(payload: dict, field: str, maxLength: int) -> str:
    value = payload.get(field)
    if value is None:
        return ''
    if not isinstance(value, str):
        raise SharingGroupError(f'`{field}` must be a text', field=field)
    value = value.strip()
    if len(value) > maxLength:
        raise SharingGroupError(f'`{field}` is too long (at most {maxLength} characters)', field=field)
    return value


def cleanFlag(payload: dict, field: str) -> bool:
    if not isinstance(payload[field], bool):
        raise SharingGroupError(f'`{field}` must be true or false', field=field)
    return payload[field]


def cleanUuid(value, what: str, field: str) -> str:
    uuid = value.strip().lower() if isinstance(value, str) else ''
    if not UUID_RE.match(uuid):
        raise SharingGroupError(f'{what} must be a UUID, such as 5f6e7d8c-1a2b-4c3d-8e9f-0a1b2c3d4e5f', field=field)
    return uuid


def cleanMembers(value) -> List[dict]:
    """`[{uuid, name, extend?}]`: organisations of the server, by UUID (the name is what MISP shows if it has to
    create one)"""
    if not isinstance(value, list):
        raise SharingGroupError('`members` must be a list of organisations', field='members')
    if len(value) > MAX_MEMBERS:
        raise SharingGroupError(f'A sharing group has at most {MAX_MEMBERS} members here', field='members')
    members = {}
    for member in value:
        if not isinstance(member, dict):
            raise SharingGroupError('Each member is an organisation: `{uuid, name, extend}`', field='members')
        uuid = cleanUuid(member.get('uuid'), 'A member’s `uuid`', 'members')
        name = cleanText(member, 'name', MAX_NAME_LENGTH)
        if not name:
            raise SharingGroupError('Each member needs the organisation’s name', field='members')
        extend = member.get('extend', False)
        if not isinstance(extend, bool):
            raise SharingGroupError('A member’s `extend` must be true or false', field='members')
        members[uuid] = {'uuid': uuid, 'name': name, 'extend': extend}
    return list(members.values())


def cleanServers(value) -> List[dict]:
    """`[{server_id, all_orgs?, name?}]`: the sync servers of the MISP server, by their ID there; 0 is the "Local
    instance". The name only names the server in what is reported"""
    if not isinstance(value, list):
        raise SharingGroupError('`servers` must be a list of servers', field='servers')
    if len(value) > MAX_SERVERS:
        raise SharingGroupError(f'A sharing group has at most {MAX_SERVERS} servers here', field='servers')
    servers = {}
    for server in value:
        serverId = server.get('server_id') if isinstance(server, dict) else None
        if isinstance(serverId, bool) or not isinstance(serverId, int) or serverId < 0:
            raise SharingGroupError('Each server is `{server_id, all_orgs}`, `server_id` being its ID on MISP '
                                    '(0 for the Local instance)', field='servers')
        allOrgs = server.get('all_orgs', False)
        if not isinstance(allOrgs, bool):
            raise SharingGroupError('A server’s `all_orgs` must be true or false', field='servers')
        servers[serverId] = {'server_id': serverId, 'all_orgs': allOrgs}
        name = server.get('name')
        if isinstance(name, str) and name.strip():
            servers[serverId]['name'] = name.strip()[:MAX_NAME_LENGTH]
    return list(servers.values())


def cleanRequest(payload, partial: bool = False) -> dict:
    """The fields of an add (`partial` False) or edit request, checked. An edit keeps only the fields given;
    `members` and `servers` are then the whole new lists"""
    if not isinstance(payload, dict):
        raise SharingGroupError('The sharing group must be an object')
    unknown = sorted(set(payload) - set(REQUEST_FIELDS))
    if unknown:
        raise SharingGroupError(f"Unknown field{'s' if len(unknown) > 1 else ''}: {', '.join(unknown)}",
                                field=unknown[0])
    fields = {}
    if not partial or 'name' in payload:
        name = cleanText(payload, 'name', MAX_NAME_LENGTH)
        if not name:
            raise SharingGroupError('A name is required', field='name')
        fields['name'] = name
    if 'uuid' in payload:
        if partial:
            raise SharingGroupError('A sharing group keeps its UUID', field='uuid')
        if payload['uuid'] not in (None, ''):
            fields['uuid'] = cleanUuid(payload['uuid'], '`uuid`', 'uuid')
    for field in ('description', 'releasability'):
        if field in payload:
            fields[field] = cleanText(payload, field, MAX_TEXT_LENGTH)
    for field in ('active', 'roaming'):
        if field in payload:
            fields[field] = cleanFlag(payload, field)
    if 'members' in payload:
        fields['members'] = cleanMembers(payload['members'])
    if 'servers' in payload:
        fields['servers'] = cleanServers(payload['servers'])
    if partial and not fields:
        raise SharingGroupError('Nothing to change')
    return fields


def cachedName(server: Server, uuid: str) -> Optional[str]:
    """The group's name as last listed, to title what is done to it"""
    try:
        group = findGroup(sharingGroupsOf(server)['sharing_groups'], uuid)
    except mispOps.MispOpError:
        return None
    return group['name'] if group else None


def checkNameFree(server: Server, name: str, uuid: Optional[str] = None) -> None:
    """MISP renames a group whose name is taken (`name_<n>`) rather than refuse it: refused here instead. Read from
    the cached list (the write checks MISP again)"""
    groups = sharingGroupsOf(server)['sharing_groups']
    clash = next((group for group in groups
                  if group['uuid'] != uuid and normalisedName(group['name']) == normalisedName(name)), None)
    if clash is not None:
        raise SharingGroupError(f"A sharing group named `{clash['name']}` is already on this server", 409,
                                field='name')


# Writes on the server. Each step is described, so that a partial failure says what was done and what was not

class Steps:
    def __init__(self):
        self.done: List[str] = []
        self.failed: List[str] = []

    def run(self, description: str, call: Callable[[], None]) -> bool:
        try:
            call()
        except mispOps.MispOpError as e:
            self.failed.append(f'{description}: {e.message}')
            return False
        self.done.append(description)
        return True

    def summary(self) -> str:
        parts = []
        if self.done:
            parts.append(f"Done: {'; '.join(self.done)}")
        if self.failed:
            parts.append(f"Failed: {'; '.join(self.failed)}")
        return '. '.join(parts)


def localServerRow(server: Server, allOrgs: bool) -> dict:
    """MISP knows its own "Local instance" row by its base URL"""
    baseurl = mispOps.getSetting(server, 'MISP.baseurl')
    if not isinstance(baseurl, str) or not baseurl:
        raise mispOps.MispOpError('MISP.baseurl is not set on this server, so the Local instance row cannot be set')
    return {'all_orgs': allOrgs, 'Server': {'url': baseurl, 'all_orgs': allOrgs}}


def memberRow(member: dict) -> dict:
    return {'extend': member['extend'], 'Organisation': {'uuid': member['uuid'], 'name': member['name']}}


def serverName(server_id: int, names: Dict[int, str]) -> str:
    return LOCAL_INSTANCE_NAME if server_id == LOCAL_INSTANCE else names.get(server_id, f'server #{server_id}')


def outcome(server: Server, uuid: str, steps: Steps) -> dict:
    """The group as MISP now has it, with what was done; `error` when a step failed"""
    forget([server])
    group = None
    try:
        group = findGroup(sharingGroupsOf(server, refresh=True)['sharing_groups'], uuid)
    except mispOps.MispOpError:
        pass
    result = {'SharingGroup': group, 'done': steps.done, 'failed': steps.failed}
    if steps.failed:
        result['error'] = steps.summary()
    return result


def addSharingGroup(server: Server, fields: dict) -> dict:
    """Created by capture, as sync does: MISP then lists it as received by sync. The "Local instance" row is given
    when it lets all organisations in (else MISP adds it itself when the group does not roam); other servers are
    added once the group exists"""
    groups = listFromMisp(server)
    clash = next((group for group in groups if normalisedName(group['name']) == normalisedName(fields['name'])), None)
    if clash is not None:
        raise mispOps.MispOpError(f"A sharing group named `{clash['name']}` is already on this server")
    uuid = fields.get('uuid') or str(uuidLib.uuid4())
    if findGroup(groups, uuid) is not None:
        raise mispOps.MispOpError('A sharing group with this UUID is already on this server')
    roaming = fields.get('roaming', False)
    servers = [] if roaming else fields.get('servers', [])
    body = {'uuid': uuid, 'name': fields['name'], 'description': fields.get('description', ''),
            'releasability': fields.get('releasability', ''), 'active': fields.get('active', True),
            'roaming': roaming, 'SharingGroupOrg': [memberRow(member) for member in fields.get('members', [])]}
    local = next((row for row in servers if row['server_id'] == LOCAL_INSTANCE), None)
    try:
        if local is not None and local['all_orgs']:
            body['SharingGroupServer'] = [localServerRow(server, True)]
        mispOps.captureSharingGroup(server, body)
    finally:
        forget([server])
    steps = Steps()
    steps.done.append('created')
    for row in servers:
        if row['server_id'] != LOCAL_INSTANCE:
            steps.run(f"{row.get('name') or serverName(row['server_id'], {})} added",
                      lambda row=row: mispOps.addSharingGroupServer(server, uuid, row['server_id'], row['all_orgs']))
    return outcome(server, uuid, steps)


def replaceRow(remove: Callable[[], None], add: Callable[[bool], None], flag: bool) -> None:
    """MISP has no call to change the flag of a member or server row: it is taken out and put back. When putting it
    back fails, the row is put back as it was rather than left out"""
    remove()
    try:
        add(flag)
    except mispOps.MispOpError as e:
        try:
            add(not flag)
        except mispOps.MispOpError:
            raise mispOps.MispOpError(f'{e.message} (it was taken out first and could not be put back)', e.response)
        raise


def planMembers(steps: Steps, server: Server, uuid: str, current: dict, wanted: List[dict]) -> None:
    have = {member['uuid']: member for member in current['members']}
    want = {member['uuid']: member for member in wanted}
    for member in wanted:
        known = have.get(member['uuid'])
        if known is None:
            steps.run(f"{member['name']} added",
                      lambda m=member: mispOps.addSharingGroupOrg(server, uuid, m['uuid'], m['extend']))
        elif known['extend'] != member['extend']:
            steps.run(f"{member['name']} {'may' if member['extend'] else 'may no longer'} extend the group",
                      lambda m=member: replaceRow(
                          lambda: mispOps.removeSharingGroupOrg(server, uuid, m['uuid']),
                          lambda extend: mispOps.addSharingGroupOrg(server, uuid, m['uuid'], extend), m['extend']))
    for member in current['members']:
        if member['uuid'] not in want:
            steps.run(f"{member['name']} removed",
                      lambda m=member: mispOps.removeSharingGroupOrg(server, uuid, m['uuid']))


def planServers(steps: Steps, server: Server, uuid: str, current: dict, wanted: List[dict]) -> None:
    have = {row['server_id']: row for row in current['servers']}
    names = {row['server_id']: row['name'] for row in current['servers']}
    want = {row['server_id']: row for row in wanted}
    local, known = want.get(LOCAL_INSTANCE), have.get(LOCAL_INSTANCE)
    if local is not None and (known is None or known['all_orgs'] != local['all_orgs']):
        steps.run(f"{LOCAL_INSTANCE_NAME} {'open to' if local['all_orgs'] else 'limited to the members, not'} "
                  f"all its organisations",
                  lambda: mispOps.editSharingGroup(server, uuid, {}, [localServerRow(server, local['all_orgs'])]))
    elif local is None and known is not None:
        steps.failed.append(f'{LOCAL_INSTANCE_NAME} not removed: MISP only lets its own interface remove it')
    for row in wanted:
        if row['server_id'] == LOCAL_INSTANCE:
            continue
        before = have.get(row['server_id'])
        name = row.get('name') or serverName(row['server_id'], names)
        if before is None:
            steps.run(f'{name} added',
                      lambda r=row: mispOps.addSharingGroupServer(server, uuid, r['server_id'], r['all_orgs']))
        elif before['all_orgs'] != row['all_orgs']:
            steps.run(f"{name} {'open to all its organisations' if row['all_orgs'] else 'limited to the members'}",
                      lambda r=row: replaceRow(
                          lambda: mispOps.removeSharingGroupServer(server, uuid, r['server_id']),
                          lambda allOrgs: mispOps.addSharingGroupServer(server, uuid, r['server_id'], allOrgs),
                          r['all_orgs']))
    for row in current['servers']:
        if row['server_id'] != LOCAL_INSTANCE and row['server_id'] not in want:
            steps.run(f"{row['name']} removed",
                      lambda r=row: mispOps.removeSharingGroupServer(server, uuid, r['server_id']))


def editSharingGroup(server: Server, uuid: str, changes: dict) -> dict:
    """Applies what differs from the group as MISP has it now: its attributes, then its members, then its servers.
    Server lists are left alone for a roaming group (MISP ignores them)"""
    current = findGroup(listFromMisp(server), uuid)
    if current is None:
        raise mispOps.MispOpError('This sharing group is not on the server any more')
    steps = Steps()
    attributes = {field: changes[field] for field in ATTRIBUTES if field in changes and changes[field] != current[field]}
    if attributes:
        steps.run(f"{', '.join(sorted(attributes))} changed",
                  lambda: mispOps.editSharingGroup(server, uuid, attributes))
    if 'members' in changes:
        planMembers(steps, server, uuid, current, changes['members'])
    roaming = changes.get('roaming', current['roaming'])
    if 'servers' in changes and not roaming:
        planServers(steps, server, uuid, current, changes['servers'])
    return outcome(server, uuid, steps)


def deleteSharingGroup(server: Server, uuid: str) -> dict:
    try:
        mispOps.deleteSharingGroup(server, uuid)
    except mispOps.MispOpError as e:
        status = e.response.status_code if e.response is not None else None
        if status == 403:
            raise mispOps.MispOpError('MISP refused to delete it: events, attributes, objects or reports still use '
                                      f'this sharing group ({e.message})', e.response)
        if status in (404, 405):
            raise mispOps.MispOpError('MISP does not let the API user delete this sharing group, or it is gone '
                                      f'({e.message})', e.response)
        raise
    finally:
        forget([server])
    return {'deleted': uuid}


def asOperationResult(call: Callable[[], dict]) -> dict:
    """A server-management result for the job unit, `{"error": …}` when MISP refused"""
    try:
        return call()
    except mispOps.MispOpError as e:
        result = {'error': e.message}
        if e.response is not None:
            result['_status_code'] = e.response.status_code
        return result


def operationUuid(params: dict) -> Optional[str]:
    uuid = params.get('uuid')
    return uuid if isinstance(uuid, str) and UUID_RE.match(uuid) else None


def addOperation(server: Server, params: dict) -> dict:
    return asOperationResult(lambda: addSharingGroup(server, params.get('payload') or {}))


def editOperation(server: Server, params: dict) -> dict:
    uuid = operationUuid(params)
    if uuid is None:
        return {'error': 'A sharing group UUID is required'}
    return asOperationResult(lambda: editSharingGroup(server, uuid, params.get('payload') or {}))


def deleteOperation(server: Server, params: dict) -> dict:
    uuid = operationUuid(params)
    if uuid is None:
        return {'error': 'A sharing group UUID is required'}
    return asOperationResult(lambda: deleteSharingGroup(server, uuid))


# Members on another server (copy job, baseline fixes)

def addMembers(server: Server, uuid: str, members: List[dict]) -> Tuple[int, int]:
    """Adds `members` (`[{uuid, name, extend}]`) to the server's group, creating first, as external organisations,
    those the server does not know (same UUID and name). Returns (members added, organisations created); raises
    MispOpError saying how far it got"""
    if not members:
        return 0, 0
    known = {org['uuid'] for org in organisationModel.listFromMisp(server)}
    added = created = 0
    try:
        for member in members:
            if member['uuid'] not in known:
                organisationModel.addOrganisation(server, {'uuid': member['uuid'], 'name': member['name'],
                                                           'local': False})
                known.add(member['uuid'])
                created += 1
            mispOps.addSharingGroupOrg(server, uuid, member['uuid'], member.get('extend') is True)
            added += 1
    except mispOps.MispOpError as e:
        done = f' ({added} of {len(members)} added before)' if added else ''
        raise mispOps.MispOpError(f"Could not add {member['name']}{done}: {e.message}", e.response)
    finally:
        forget([server])
        if created:
            organisationModel.forget([server])
    return added, created


# Create or complete on other servers (one job unit per server)

def copyParams(group: dict) -> dict:
    return {
        'sharing_group': {
            **{field: group[field] for field in ('uuid',) + ATTRIBUTES},
            'members': [{field: member[field] for field in ('uuid', 'name', 'extend')} for member in group['members']],
        },
        # Server lists name the source's own sync servers: not copied, said in the summary
        'servers_not_copied': len([row for row in group['servers'] if row['server_id'] != LOCAL_INSTANCE]),
    }


def plural(count: int, noun: str) -> str:
    return f"{count} {noun}{'' if count == 1 else 's'}"


def differenceNotes(group: dict, theirs: dict) -> List[str]:
    """Differences the copy reports and leaves as they are"""
    notes = []
    if normalisedName(theirs['name']) != normalisedName(group['name']):
        notes.append(f"named `{theirs['name']}` there")
    if theirs['active'] != group['active']:
        notes.append('active there' if theirs['active'] else 'inactive there')
    if theirs['roaming'] != group['roaming']:
        notes.append('roaming there' if theirs['roaming'] else 'not roaming there')
    return notes


def withNotes(summary: str, notes: List[str]) -> str:
    return f"{summary} ({', '.join(notes)}, left as it is)" if notes else summary


def copyUnit(server: Server, params: dict) -> UnitResult:
    """Create the group, with its UUID, or add the members it lacks. A different group with the same name is reported
    rather than worked around: MISP would rename the copy, hiding the mismatch"""
    group = params.get('sharing_group') if isinstance(params.get('sharing_group'), dict) else {}
    uuid = mispOps.uuidKey(group.get('uuid') or '')
    name = mispOps.text(group.get('name'))
    if not UUID_RE.match(uuid) or not name:
        return UnitResult(False, summary='The sharing group to create needs a UUID and a name')
    members = [member for member in group.get('members') or []
               if isinstance(member, dict) and UUID_RE.match(str(member.get('uuid', '')))]
    try:
        groups = listFromMisp(server)
    except mispOps.MispOpError as e:
        return UnitResult(False, http_status=e.response.status_code if e.response is not None else None,
                          summary=e.message)
    store(server, groups)
    existing = findGroup(groups, uuid)
    if existing is not None:
        theirs = {member['uuid'] for member in existing['members']}
        missing = [member for member in members if member['uuid'] not in theirs]
        notes = differenceNotes(group, existing)
        if not missing:
            return UnitResult(True, summary=withNotes('Already complete', notes),
                              response={'created': False, 'added': 0, 'SharingGroup': existing})
        try:
            added, created = addMembers(server, uuid, missing)
        except mispOps.MispOpError as e:
            return UnitResult(False, http_status=e.response.status_code if e.response is not None else None,
                              summary=e.message)
        summary = f"Added {plural(added, 'member')}"
        if created:
            summary += f" ({plural(created, 'organisation')} created)"
        return UnitResult(True, summary=withNotes(summary, notes),
                          response={'created': False, 'added': added, 'organisations_created': created})
    clash = next((other for other in groups if normalisedName(other['name']) == normalisedName(name)), None)
    if clash is not None:
        return UnitResult(False, summary=f"`{clash['name']}` already exists here with another UUID ({clash['uuid']})",
                          response={'created': False, 'SharingGroup': clash})
    body = {'uuid': uuid, 'name': name, **{field: group.get(field) for field in ATTRIBUTES[1:] if field in group},
            'SharingGroupOrg': [memberRow({'uuid': member['uuid'], 'name': mispOps.text(member.get('name')),
                                           'extend': member.get('extend') is True}) for member in members]}
    try:
        mispOps.captureSharingGroup(server, body)
    except mispOps.MispOpError as e:
        return UnitResult(False, http_status=e.response.status_code if e.response is not None else None,
                          summary=e.message)
    finally:
        forget([server])
        # MISP creates the members it does not know
        organisationModel.forget([server])
    summary = 'Created'
    left = params.get('servers_not_copied')
    if isinstance(left, int) and left > 0:
        summary += f" (its {plural(left, 'server')} not copied: add them there if needed)"
    return UnitResult(True, summary=summary, response={'created': True})


def startCopy(user, server: Server, body) -> Job:
    """Queue a job creating, or completing, one of the server's sharing groups on other servers of its fleet:
    `{uuid, server_ids}`. The group is read from the server (cached list, then MISP again if it is not there)"""
    import application.models.jobs as jobModel
    import application.models.userJobs as userJobs
    if not isinstance(body, dict):
        raise SharingGroupError('Expected `{uuid, server_ids}`')
    uuid = cleanUuid(body.get('uuid'), '`uuid`', 'uuid')
    serverIds = body.get('server_ids')
    if not isinstance(serverIds, list) or not serverIds or \
            any(isinstance(id, bool) or not isinstance(id, int) for id in serverIds):
        raise SharingGroupError('`server_ids` must be a non-empty list of server IDs', field='server_ids')
    serverIds = list(dict.fromkeys(serverIds))
    if server.id in serverIds:
        raise SharingGroupError('The sharing group is already on this server', field='server_ids')
    targets = Server.query.filter(Server.id.in_(serverIds), Server.user_id == user.id).all()
    found = {target.id for target in targets}
    missing = [str(id) for id in serverIds if id not in found]
    if missing:
        raise SharingGroupError(f"Unknown server{'s' if len(missing) > 1 else ''}: {', '.join(missing)}", 404)
    elsewhere = [target.name for target in targets if target.fleet_id != server.fleet_id]
    if elsewhere:
        raise SharingGroupError(f"Only servers of the same fleet can be chosen, not: {', '.join(sorted(elsewhere))}",
                                field='server_ids')
    source = None
    for refresh in (False, True):
        source = findGroup(sharingGroupsOf(server, refresh=refresh)['sharing_groups'], uuid)
        if source is not None:
            break
    if source is None:
        raise SharingGroupError('Unknown sharing group: it is not on this server', 404, field='uuid')
    targets.sort(key=lambda target: (target.name.lower(), target.id))
    where = targets[0].name if len(targets) == 1 else f'{len(targets)} servers'
    job = jobModel.create(user, 'sharing_group_copy', targets, params=copyParams(source),
                          title=f"Sharing group {source['name']} on {where}", fleet=server.fleet)
    return userJobs.enqueue(job)
