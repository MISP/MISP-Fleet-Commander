#!/usr/bin/env python3
"""The organisations of a MISP server, as its Remote administration tab shows them: listed live from MISP and kept a
few minutes, compared with the other servers of its fleet, created, edited and copied to other servers"""

import json
import re
from typing import Dict, Iterable, List, Optional

import application.models.mispOps as mispOps
import application.models.organisationDigests as organisationDigests
from application.DBModels import Job, Server
from application.models.jobs import UnitResult
from application.models.organisationDigests import normalisedName
from application.models.remoteLists import FLEET_TIMEOUT, ListCache, RemoteListError, gatherFleet
from application.redisModel import KEY_SERVER_ORGANISATIONS

MAX_NAME_LENGTH = 255
MAX_TEXT_LENGTH = 255
MAX_LONG_TEXT_LENGTH = 65535
TEXT_FIELDS = ('type', 'nationality', 'sector')
LONG_TEXT_FIELDS = ('description', 'contacts')
EDITABLE_FIELDS = ('name', 'uuid', 'local') + TEXT_FIELDS + LONG_TEXT_FIELDS + ('restricted_to_domain',)
# What a copy carries to another server. Restricted domains are a policy of each instance for its own users
COPIED_FIELDS = ('name',) + TEXT_FIELDS + LONG_TEXT_FIELDS
UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')


class OrganisationError(RemoteListError):
    pass


# Records

def domainList(value) -> List[str]:
    """MISP decodes `restricted_to_domain` into a list; older versions or empty values may give a string"""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            value = re.split(r'[\n,]', value)
    if not isinstance(value, list):
        return []
    return [str(domain).strip() for domain in value if str(domain).strip()]


def compact(record: dict) -> dict:
    """What the tab needs of a MISP organisation record. `user_count` is None when MISP does not give it"""
    userCount = record.get('user_count')
    return {
        'id': mispOps.number(record.get('id')),
        'uuid': mispOps.uuidKey(record.get('uuid') or ''),
        'name': mispOps.text(record.get('name')),
        'local': mispOps.flag(record.get('local')),
        **{field: mispOps.text(record.get(field)) for field in TEXT_FIELDS + LONG_TEXT_FIELDS},
        'restricted_to_domain': domainList(record.get('restricted_to_domain')),
        'date_created': record.get('date_created') or None,
        'date_modified': record.get('date_modified') or None,
        'created_by_email': record.get('created_by_email') or None,
        'user_count': None if userCount is None or userCount == '' else mispOps.number(userCount),
    }


def parse(records: Iterable[dict]) -> List[dict]:
    """Sorted by name. Records without a UUID cannot be compared or copied, so they are left out"""
    organisations = [compact(record) for record in records if isinstance(record, dict) and record.get('uuid')]
    return sorted(organisations, key=lambda org: (org['name'].lower(), org['uuid']))


# Cache

class OrganisationCache(ListCache):
    """Every listing also replaces the server's digest, which the fleet's health compares (see
    `organisationDigests`). `publish_self=False` when the caller publishes the server's health itself"""

    def store(self, server: Server, items: List[dict], now: Optional[int] = None, publish_self: bool = True) -> dict:
        listed = super().store(server, items, now)
        organisationDigests.remember(server, items, now=listed['fetched_at'], publish_self=publish_self)
        return listed


CACHE = OrganisationCache(KEY_SERVER_ORGANISATIONS, 'organisations')
readCached = CACHE.read
store = CACHE.store
forget = CACHE.forget


def listFromMisp(server: Server) -> List[dict]:
    return parse(mispOps.listing(server, *mispOps.ORGANISATION_INDEX))


def organisationsOf(server: Server, refresh: bool = False) -> dict:
    """`{fetched_at, cached, organisations}`. Raises MispOpError when MISP cannot list them (failures are not cached)"""
    if not refresh:
        cached = readCached(server)
        if cached is not None:
            return {**cached, 'cached': True}
    return {**store(server, listFromMisp(server)), 'cached': False}


# Comparison with the other servers of the fleet

def compare(own: List[dict], others: Dict[int, List[dict]]) -> Dict[str, dict]:
    """For each organisation of `own` (by UUID), the other servers where it is: `same` (same UUID and name), `renamed`
    (same UUID, `[server_id, their name]`), `other_uuid` (no such UUID, but one with the same name: `[server_id, its
    UUID]`). Compared servers missing from all three do not have it"""
    indexes = {}
    for server_id, organisations in others.items():
        byUuid = {org['uuid']: org for org in organisations}
        byName = {}
        for org in organisations:
            byName.setdefault(normalisedName(org['name']), org)
        indexes[server_id] = (byUuid, byName)
    result = {}
    for org in own:
        entry = {'same': [], 'renamed': [], 'other_uuid': []}
        name = normalisedName(org['name'])
        for server_id, (byUuid, byName) in indexes.items():
            theirs = byUuid.get(org['uuid'])
            if theirs is not None:
                if normalisedName(theirs['name']) == name:
                    entry['same'].append(server_id)
                else:
                    entry['renamed'].append([server_id, theirs['name']])
            elif name in byName:
                entry['other_uuid'].append([server_id, byName[name]['uuid']])
        result[org['uuid']] = entry
    return result


def decodeList(answers: list) -> List[dict]:
    """The organisations of another client's decoded index answer"""
    return parse(mispOps.decodedRecords(answers[0], *mispOps.ORGANISATION_INDEX[1:]))


def listedByRefresh(server: Server, answer) -> None:
    """The organisations a full refresh listed (the decoded index answer): kept for the tab and as the server's
    digest. The refresh publishes the server's health itself. Never raises: a failed listing keeps the previous
    digest, which expires on its own"""
    try:
        organisations = decodeList([answer])
    except mispOps.MispOpError:
        return
    except Exception as e:
        print(f'Could not read the organisations of server {server.id}: {e}')
        return
    try:
        CACHE.store(server, organisations, publish_self=False)
    except Exception as e:
        print(f'Could not keep the organisations of server {server.id}: {e}')


def listedByRefreshUrl(server: Server) -> Optional[str]:
    """The index a full refresh lists for the fleet's health: only when the server has another server in its fleet
    to compare with"""
    if server.fleet_id is None:
        return None
    other = Server.query.filter(Server.fleet_id == server.fleet_id, Server.id != server.id).first()
    return mispOps.ORGANISATION_INDEX[0] if other is not None else None


def fleetComparison(server: Server, refresh: bool = False) -> dict:
    """How the server's organisations compare with the rest of its fleet. Lists come from the cache when fresh,
    else are read now. Servers whose list could not be read are `unavailable`, never counted as missing it"""
    own = organisationsOf(server, refresh=refresh)['organisations']
    url, _, what = mispOps.ORGANISATION_INDEX
    fleet = gatherFleet(server, CACHE, [url], decodeList, what, refresh=refresh, timeout=FLEET_TIMEOUT)
    return {
        'server_id': server.id,
        'fleet_id': server.fleet_id,
        'compared': fleet['compared'],
        'unavailable': fleet['unavailable'],
        'organisations': compare(own, fleet['lists']),
    }


# Writes

def cleanText(payload: dict, field: str, maxLength: int) -> str:
    value = payload.get(field)
    if value is None:
        return ''
    if not isinstance(value, str):
        raise OrganisationError(f'`{field}` must be a text', field=field)
    value = value.strip()
    if len(value) > maxLength:
        raise OrganisationError(f'`{field}` is too long (at most {maxLength} characters)', field=field)
    return value


def cleanDomains(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = re.split(r'[\n,]', value)
    if not isinstance(value, list) or any(not isinstance(domain, str) for domain in value):
        raise OrganisationError('`restricted_to_domain` must be a list of domains', field='restricted_to_domain')
    domains = [domain.strip() for domain in value if domain.strip()]
    for domain in domains:
        if len(domain) > MAX_TEXT_LENGTH or re.search(r'\s', domain):
            raise OrganisationError(f'`{domain}` is not a domain', field='restricted_to_domain')
    return domains


def cleanFields(payload, partial: bool = False) -> dict:
    """The organisation fields of a request, checked. `partial` (edit) keeps only the fields given"""
    if not isinstance(payload, dict):
        raise OrganisationError('The organisation must be an object')
    unknown = sorted(set(payload) - set(EDITABLE_FIELDS))
    if unknown:
        raise OrganisationError(f"Unknown field{'s' if len(unknown) > 1 else ''}: {', '.join(unknown)}",
                                field=unknown[0])
    fields = {}
    if not partial or 'name' in payload:
        name = cleanText(payload, 'name', MAX_NAME_LENGTH)
        if not name:
            raise OrganisationError('A name is required', field='name')
        fields['name'] = name
    if 'uuid' in payload and payload['uuid'] not in (None, ''):
        uuid = payload['uuid'].strip().lower() if isinstance(payload['uuid'], str) else None
        if uuid is None or not UUID_RE.match(uuid):
            raise OrganisationError('`uuid` must be a UUID, such as 5f6e7d8c-1a2b-4c3d-8e9f-0a1b2c3d4e5f',
                                    field='uuid')
        fields['uuid'] = uuid
    elif 'uuid' in payload and partial:
        raise OrganisationError('An organisation keeps a UUID: give one, or leave it out', field='uuid')
    if 'local' in payload:
        if not isinstance(payload['local'], bool):
            raise OrganisationError('`local` must be true or false', field='local')
        fields['local'] = payload['local']
    for field in TEXT_FIELDS:
        if field in payload:
            fields[field] = cleanText(payload, field, MAX_TEXT_LENGTH)
    for field in LONG_TEXT_FIELDS:
        if field in payload:
            fields[field] = cleanText(payload, field, MAX_LONG_TEXT_LENGTH)
    if 'restricted_to_domain' in payload:
        fields['restricted_to_domain'] = cleanDomains(payload['restricted_to_domain'])
    if partial and not fields:
        raise OrganisationError('Nothing to change')
    return fields


def mispPayload(fields: dict) -> dict:
    """MISP takes the restricted domains one per line (every version reads that form)"""
    payload = dict(fields)
    if 'restricted_to_domain' in payload:
        payload['restricted_to_domain'] = '\n'.join(payload['restricted_to_domain'])
    return {'Organisation': payload}


def savedRecord(response) -> Optional[dict]:
    data = mispOps.responseJson(response)
    record = data.get('Organisation') if isinstance(data, dict) else None
    return compact(record) if isinstance(record, dict) and record.get('uuid') else None


def addOrganisation(server: Server, fields: dict) -> Optional[dict]:
    """The organisation MISP created, when it answers it. MISP makes it local when `local` is not given"""
    try:
        response = mispOps.post(server, '/admin/organisations/add', mispPayload(fields))
    except mispOps.MispOpError as e:
        raise mispOps.MispOpError(f"Could not create organisation `{fields.get('name', '')}`: {e.message}",
                                  e.response)
    finally:
        forget([server])
    return savedRecord(response)


def editOrganisation(server: Server, org_id: int, changes: dict) -> Optional[dict]:
    try:
        response = mispOps.post(server, f'/admin/organisations/edit/{int(org_id)}', mispPayload(changes))
    except mispOps.MispOpError as e:
        raise mispOps.MispOpError(f'Could not change the organisation: {e.message}', e.response)
    finally:
        forget([server])
    return savedRecord(response)


def asOperationResult(call) -> dict:
    """A user-administration style result for the job unit: `{"Organisation": …}`, or `{"error": …, "_status_code"}`"""
    try:
        return {'Organisation': call()}
    except mispOps.MispOpError as e:
        result = {'error': e.message}
        if e.response is not None:
            result['_status_code'] = e.response.status_code
        return result


def addOperation(server: Server, params: dict) -> dict:
    return asOperationResult(lambda: addOrganisation(server, params.get('payload') or {}))


def editOperation(server: Server, params: dict) -> dict:
    if not isinstance(params.get('org_id'), int) or isinstance(params.get('org_id'), bool):
        return {'error': 'An organisation ID is required'}
    return asOperationResult(lambda: editOrganisation(server, params['org_id'], params.get('payload') or {}))


# Copy to other servers (one job unit per server)

def copyParams(organisation: dict, local: bool) -> dict:
    return {
        'organisation': {'uuid': organisation['uuid'],
                         **{field: organisation.get(field) or '' for field in COPIED_FIELDS}},
        'local': bool(local),
    }


def copyUnit(server: Server, params: dict) -> UnitResult:
    """Create the organisation, with its UUID, unless the server already has it. A different organisation with the
    same name is reported rather than worked around: MISP refuses a second one, and it is the mismatch to fix"""
    org = params.get('organisation') if isinstance(params.get('organisation'), dict) else {}
    uuid = mispOps.uuidKey(org.get('uuid') or '')
    name = mispOps.text(org.get('name'))
    if not UUID_RE.match(uuid) or not name:
        return UnitResult(False, summary='The organisation to create needs a UUID and a name')
    try:
        organisations = listFromMisp(server)
    except mispOps.MispOpError as e:
        return UnitResult(False, http_status=e.response.status_code if e.response is not None else None,
                          summary=e.message)
    store(server, organisations)
    existing = next((candidate for candidate in organisations if candidate['uuid'] == uuid), None)
    if existing is not None:
        summary = 'Already there'
        if normalisedName(existing['name']) != normalisedName(name):
            summary = f"Already there, named `{existing['name']}` (left as it is)"
        return UnitResult(True, summary=summary, response={'created': False, 'Organisation': existing})
    clash = next((candidate for candidate in organisations
                  if normalisedName(candidate['name']) == normalisedName(name)), None)
    if clash is not None:
        return UnitResult(False, summary=f"`{clash['name']}` already exists here with another UUID ({clash['uuid']})",
                          response={'created': False, 'Organisation': clash})
    local = bool(params.get('local'))
    fields = {'uuid': uuid, 'name': name, 'local': local,
              **{field: mispOps.text(org.get(field)) for field in COPIED_FIELDS[1:] if mispOps.text(org.get(field))}}
    try:
        created = addOrganisation(server, fields)
    except mispOps.MispOpError as e:
        return UnitResult(False, http_status=e.response.status_code if e.response is not None else None,
                          summary=e.message)
    return UnitResult(True, summary=f"Created{' (local)' if local else ''}",
                      response={'created': True, 'Organisation': created})


def startCopy(user, server: Server, body) -> Job:
    """Queue a job creating one of the server's organisations on other servers of its fleet: `{uuid, server_ids,
    local?}`. The organisation is read from the server (cached list, then MISP again if it is not there)"""
    import application.models.jobs as jobModel
    import application.models.userJobs as userJobs
    if not isinstance(body, dict):
        raise OrganisationError('Expected `{uuid, server_ids, local?}`')
    uuid = body.get('uuid').strip().lower() if isinstance(body.get('uuid'), str) else ''
    if not UUID_RE.match(uuid):
        raise OrganisationError('`uuid` must be the UUID of one of the server\'s organisations', field='uuid')
    serverIds = body.get('server_ids')
    if not isinstance(serverIds, list) or not serverIds or \
            any(isinstance(id, bool) or not isinstance(id, int) for id in serverIds):
        raise OrganisationError('`server_ids` must be a non-empty list of server IDs', field='server_ids')
    serverIds = list(dict.fromkeys(serverIds))
    if server.id in serverIds:
        raise OrganisationError('The organisation is already on this server', field='server_ids')
    local = body.get('local', False)
    if not isinstance(local, bool):
        raise OrganisationError('`local` must be true or false', field='local')
    targets = Server.query.filter(Server.id.in_(serverIds), Server.user_id == user.id).all()
    found = {target.id for target in targets}
    missing = [str(id) for id in serverIds if id not in found]
    if missing:
        raise OrganisationError(f"Unknown server{'s' if len(missing) > 1 else ''}: {', '.join(missing)}", 404)
    elsewhere = [target.name for target in targets if target.fleet_id != server.fleet_id]
    if elsewhere:
        raise OrganisationError(f"Only servers of the same fleet can be chosen, not: {', '.join(sorted(elsewhere))}",
                                field='server_ids')
    source = None
    for refresh in (False, True):
        listed = organisationsOf(server, refresh=refresh)['organisations']
        source = next((org for org in listed if org['uuid'] == uuid), None)
        if source is not None:
            break
    if source is None:
        raise OrganisationError('Unknown organisation: it is not on this server', 404, field='uuid')
    targets.sort(key=lambda target: (target.name.lower(), target.id))
    where = targets[0].name if len(targets) == 1 else f'{len(targets)} servers'
    job = jobModel.create(user, 'organisation_copy', targets, params=copyParams(source, local),
                          title=f"Create organisation {source['name']} on {where}", fleet=server.fleet)
    return userJobs.enqueue(job)
