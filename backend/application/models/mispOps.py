#!/usr/bin/env python3
"""Reads and writes of a MISP server's configuration and content, shared by the plugins and baseline remediation so
that both behave the same. Every function raises MispOpError with a readable reason when MISP cannot be reached,
refuses the request or answers something unexpected"""

from typing import Any, Dict, Optional
from urllib.parse import quote

from application.controllers.utils import mispGetRequest, mispPostRequest, mispRequestError, responseJson


class MispOpError(Exception):
    def __init__(self, message: str, response: Any = None):
        super().__init__(message)
        self.message = message
        # The `requests.Response` when MISP answered, for the HTTP status
        self.response = response if not isinstance(response, dict) else None


def checked(result, context: Optional[str] = None):
    """The `requests.Response` of a raw request helper call, or MispOpError"""
    error = mispRequestError(result)
    if error is not None:
        raise MispOpError(f'{context}: {error}' if context else error, result)
    return result


def records(data, model: str, what: str, response=None) -> list:
    """The records of a MISP index answer (`[{model: {…}}, …]`), already decoded"""
    if not isinstance(data, list) or any(not isinstance(entry, dict) or model not in entry for entry in data):
        raise MispOpError(f'Could not list the {what}: unexpected answer', response)
    return [entry[model] for entry in data]


def listing(server, url: str, model: str, what: str) -> list:
    """The records of a MISP index"""
    response = checked(mispGetRequest(server, url, {}, rawResponse=True, nocache=True), f'Could not list the {what}')
    return records(responseJson(response), model, what, response)


def decodedRecords(data, model: str, what: str) -> list:
    """The records of an index fetched by another client (the refresh's async fetcher), which answers the decoded
    JSON or an error object"""
    if isinstance(data, dict):
        status = data.get('_status_code')
        if 'error' in data:
            raise MispOpError(f"Could not list the {what}: {data['error']}")
        if isinstance(status, int) and status >= 400:
            reason = data.get('message') or data.get('name') or ''
            raise MispOpError(f"Could not list the {what}: HTTP {status}{f': {reason}' if reason else ''}")
    return records(data, model, what)


def flag(value) -> bool:
    return value is True or str(value).strip().lower() in ('1', 'true')


def number(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def uuidKey(uuid) -> str:
    """UUIDs are compared lowercased: MISP ships a few in uppercase"""
    return str(uuid).strip().lower()


def post(server, url: str, payload: Optional[dict] = None):
    return checked(mispPostRequest(server, url, payload or {}, rawResponse=True, nocache=True))


# Taxonomies, by namespace

TAXONOMY_INDEX = ('/taxonomies/index', 'Taxonomy', 'taxonomies')


def taxonomies(server) -> Dict[str, dict]:
    return parseTaxonomies(listing(server, *TAXONOMY_INDEX))


def parseTaxonomies(taxonomyRecords: list) -> Dict[str, dict]:
    """namespace → {id, enabled}"""
    return {
        taxonomy['namespace']: {'id': int(taxonomy['id']), 'enabled': flag(taxonomy.get('enabled'))}
        for taxonomy in taxonomyRecords
    }


def setTaxonomyEnabled(server, taxonomyId: int, enabled: bool) -> None:
    """Enabling also creates the taxonomy's tags, as MISP's own UI offers"""
    if not enabled:
        post(server, f'/taxonomies/disable/{taxonomyId}')
        return
    post(server, f'/taxonomies/enable/{taxonomyId}')
    try:
        post(server, f'/taxonomies/addTag/{taxonomyId}')
    except MispOpError as e:
        raise MispOpError(f'Enabled, but its tags could not be created: {e.message}', e.response)


# Galaxies, by UUID (the same on every instance for the galaxies MISP ships), lowercased

GALAXY_INDEX = ('/galaxies/index', 'Galaxy', 'galaxies')


def galaxies(server) -> Dict[str, dict]:
    return parseGalaxies(listing(server, *GALAXY_INDEX))


def parseGalaxies(galaxyRecords: list) -> Dict[str, dict]:
    """uuid → {id, enabled, name, namespace, type}"""
    return {
        uuidKey(galaxy['uuid']): {
            'id': int(galaxy['id']),
            'enabled': flag(galaxy.get('enabled', True)),
            'name': galaxy.get('name') or '',
            'namespace': galaxy.get('namespace') or '',
            'type': galaxy.get('type') or '',
        }
        for galaxy in galaxyRecords
    }


def setGalaxyEnabled(server, galaxyId: int, enabled: bool) -> None:
    post(server, f"/galaxies/{'enable' if enabled else 'disable'}/{galaxyId}")


# Object templates, by UUID, lowercased

OBJECT_TEMPLATE_INDEX = ('/objectTemplates/index/all', 'ObjectTemplate', 'object templates')


def objectTemplates(server) -> Dict[str, dict]:
    return parseObjectTemplates(listing(server, *OBJECT_TEMPLATE_INDEX))


def parseObjectTemplates(templateRecords: list) -> Dict[str, dict]:
    """uuid → {id, active, name, meta_category, version}, inactive templates included. MISP keeps the earlier
    versions of a template, with the same UUID: only the latest one counts"""
    latest = {}
    for template in templateRecords:
        uuid = uuidKey(template['uuid'])
        rank = (number(template.get('version')), number(template.get('id')))
        if uuid not in latest or rank > latest[uuid][0]:
            latest[uuid] = (rank, template)
    return {
        uuid: {
            'id': int(template['id']),
            'active': flag(template.get('active')),
            'name': template.get('name') or '',
            'meta_category': template.get('meta-category') or '',
            'version': number(template.get('version')),
        }
        for uuid, (rank, template) in latest.items()
    }


def toggleObjectTemplate(server, templateId: int) -> None:
    """MISP only offers a toggle: the template's state flips"""
    post(server, '/ObjectTemplates/activate', {'ObjectTemplate': {'data': templateId}})


def setObjectTemplateActive(server, uuid: str, active: bool, templates: Optional[Dict[str, dict]] = None) -> bool:
    """Whether the template had to be toggled. `templates` (from `objectTemplates`) saves listing them again"""
    templates = templates if templates is not None else objectTemplates(server)
    template = templates.get(uuidKey(uuid))
    if template is None:
        raise MispOpError(f'Could not find object template `{uuid}`')
    if template['active'] == active:
        return False
    toggleObjectTemplate(server, template['id'])
    return True


# Settings

def settingPath(name: str) -> str:
    return quote(name, safe='')


def getSetting(server, name: str) -> Any:
    """The setting's current value, read from MISP (not from the snapshot). MISP refuses to tell redacted ones"""
    response = checked(mispGetRequest(server, f'/servers/getSetting/{settingPath(name)}', {}, rawResponse=True,
                                      nocache=True), f'Could not read `{name}`')
    data = responseJson(response)
    if not isinstance(data, dict) or 'value' not in data:
        raise MispOpError(f'Could not read `{name}`: unexpected answer', response)
    return data['value']


def editSetting(server, name: str, value: Any):
    """The `requests.Response` of the change. Saved the way MISP's own settings page saves (`force`): MISP's tests of
    a setting are diagnostics, and some fail on purpose for a valid value (`MISP.disable_emailing` set to true says
    "E-mailing is blocked."), which the API refuses without `force`. Settings MISP only lets change from its command
    line or its environment stay refused"""
    try:
        return post(server, f'/servers/serverSettingsEdit/{settingPath(name)}', {'Server': {'value': value, 'force': 1}})
    except MispOpError as e:
        raise MispOpError(f'Could not change `{name}`: {e.message}', e.response)


def snapshotSettings(serverInfo: Optional[dict]) -> Dict[str, dict]:
    """setting name → its entry in the snapshot's diagnostics (`value`, `type`, `redacted`, …), or {}"""
    try:
        finalSettings = serverInfo['query_result']['serverSettings']['finalSettings']
    except (KeyError, TypeError):
        return {}
    if not isinstance(finalSettings, list):
        return {}
    return {entry['setting']: entry for entry in finalSettings if isinstance(entry, dict) and 'setting' in entry}


# Organisations, by UUID, lowercased

ORGANISATION_INDEX = ('/organisations/index/scope:all', 'Organisation', 'organisations')
ORGANISATION_FIELDS = ('name', 'type', 'nationality', 'sector')


def text(value) -> str:
    return value.strip() if isinstance(value, str) else ''


def organisations(server) -> Dict[str, dict]:
    return parseOrganisations(listing(server, *ORGANISATION_INDEX))


def parseOrganisations(orgRecords: list) -> Dict[str, dict]:
    """uuid → {id, name, type, nationality, sector, local}"""
    return {
        uuidKey(org['uuid']): {
            'id': int(org['id']),
            **{field: text(org.get(field)) for field in ORGANISATION_FIELDS},
            'local': flag(org.get('local')),
        }
        for org in orgRecords if org.get('uuid')
    }


def addOrganisation(server, uuid: str, fields: dict, local: bool) -> None:
    """MISP makes an organisation added through its API local unless told otherwise"""
    try:
        post(server, '/admin/organisations/add', {'Organisation': {'uuid': uuid, **fields, 'local': local}})
    except MispOpError as e:
        raise MispOpError(f"Could not create organisation `{fields.get('name', uuid)}`: {e.message}", e.response)


def editOrganisation(server, orgId: int, changes: dict) -> None:
    try:
        post(server, f'/admin/organisations/edit/{orgId}', {'Organisation': changes})
    except MispOpError as e:
        raise MispOpError(f'Could not change the organisation: {e.message}', e.response)


# Sharing groups, by UUID, lowercased

SHARING_GROUP_INDEX = ('/sharing_groups/index', 'SharingGroup', 'sharing groups')


def sharingGroupRecords(data, response=None) -> list:
    """MISP wraps this index in `{"response": [...]}`"""
    if isinstance(data, dict) and isinstance(data.get('response'), list):
        data = data['response']
    if not isinstance(data, list) or any(not isinstance(entry, dict) or 'SharingGroup' not in entry for entry in data):
        raise MispOpError('Could not list the sharing groups: unexpected answer', response)
    return data


def sharingGroups(server) -> Dict[str, dict]:
    url, model, what = SHARING_GROUP_INDEX
    response = checked(mispGetRequest(server, url, {}, rawResponse=True, nocache=True), f'Could not list the {what}')
    return parseSharingGroups(sharingGroupRecords(responseJson(response), response))


def decodedSharingGroups(data) -> Dict[str, dict]:
    """From another client's decoded answer (see `decodedRecords`)"""
    if isinstance(data, dict) and not isinstance(data.get('response'), list):
        decodedRecords(data, 'SharingGroup', 'sharing groups')  # Raises with the error the answer carries
    return parseSharingGroups(sharingGroupRecords(data))


def parseSharingGroups(entries: list) -> Dict[str, dict]:
    """uuid → {id, name, releasability, description, active, roaming, members: {org uuid: {name, extend}}}"""
    groups = {}
    for entry in entries:
        sg = entry['SharingGroup']
        if not sg.get('uuid'):
            continue
        members = {}
        for member in entry.get('SharingGroupOrg') or []:
            org = member.get('Organisation') if isinstance(member, dict) else None
            if isinstance(org, dict) and org.get('uuid'):
                members[uuidKey(org['uuid'])] = {'name': text(org.get('name')), 'extend': flag(member.get('extend'))}
        groups[uuidKey(sg['uuid'])] = {
            'id': int(sg['id']),
            'name': text(sg.get('name')),
            'releasability': text(sg.get('releasability')),
            'description': text(sg.get('description')),
            'active': flag(sg.get('active')),
            'roaming': flag(sg.get('roaming')),
            'members': members,
        }
    return groups


def captureSharingGroup(server, sharingGroup: dict) -> None:
    """Creates the sharing group, or updates the one with its UUID, the way MISP takes one from a sync: the
    attributes given replace the current ones, the members listed are added (missing organisations are created as
    external ones), members not listed are kept"""
    try:
        post(server, '/sharing_groups/add', sharingGroup)
    except MispOpError as e:
        raise MispOpError(f"Could not save sharing group `{sharingGroup.get('name')}`: {e.message}", e.response)


# Custom galaxies (created on an instance, not shipped with MISP) and their clusters

def isCustomGalaxy(record: dict) -> bool:
    return not flag(record.get('default', True))


def galaxyClustersUrl(uuid: str) -> str:
    return f'/galaxy_clusters/index/{uuidKey(uuid)}'


def parseGalaxyClusters(clusterRecords: list) -> Dict[str, int]:
    """cluster uuid → version, deleted clusters left out"""
    return {
        uuidKey(cluster['uuid']): number(cluster.get('version'))
        for cluster in clusterRecords if cluster.get('uuid') and not flag(cluster.get('deleted'))
    }


def galaxyClusters(server, uuid: str) -> Optional[Dict[str, int]]:
    """The clusters of the galaxy, or None when the server has no such galaxy"""
    response = mispGetRequest(server, galaxyClustersUrl(uuid), {}, rawResponse=True, nocache=True)
    if getattr(response, 'status_code', None) == 404:
        return None
    checked(response, 'Could not list the galaxy clusters')
    return parseGalaxyClusters(records(responseJson(response), 'GalaxyCluster', 'galaxy clusters', response))


def decodedGalaxyClusters(data) -> Optional[Dict[str, int]]:
    """From another client's decoded answer: None when the server has no such galaxy"""
    if isinstance(data, dict) and data.get('_status_code') == 404:
        return None
    return parseGalaxyClusters(decodedRecords(data, 'GalaxyCluster', 'galaxy clusters'))


GALAXY_FIELDS = ('uuid', 'name', 'namespace', 'type', 'description', 'icon', 'kill_chain_order', 'distribution',
                 'category', 'sub_category', 'kind', 'local_only')


def galaxyDefinition(server, galaxyId: int) -> dict:
    """The fields a galaxy is created from"""
    response = checked(mispGetRequest(server, f'/galaxies/view/{galaxyId}', {}, rawResponse=True, nocache=True),
                       'Could not read the galaxy')
    data = responseJson(response)
    galaxy = data.get('Galaxy') if isinstance(data, dict) else None
    if not isinstance(galaxy, dict):
        raise MispOpError('Could not read the galaxy: unexpected answer', response)
    return {field: galaxy[field] for field in GALAXY_FIELDS if galaxy.get(field) is not None}


def exportGalaxyClusters(server, galaxyId: int) -> list:
    """The galaxy's custom clusters in MISP's own format, each carrying its galaxy, whatever their distribution"""
    payload = {'Galaxy': {'default': 0, 'custom': 1, 'distribution': [0, 1, 2, 3, 4], 'format': 'misp',
                          'download': 'raw'}}
    try:
        response = post(server, f'/galaxies/export/{galaxyId}', payload)
    except MispOpError as e:
        raise MispOpError(f'Could not export the galaxy clusters: {e.message}', e.response)
    data = responseJson(response)
    if not isinstance(data, list):
        raise MispOpError('Could not export the galaxy clusters: unexpected answer', response)
    return data


def importGalaxyClusters(server, clusters: list) -> None:
    try:
        post(server, '/galaxies/import', clusters)
    except MispOpError as e:
        raise MispOpError(f'Could not import the galaxy clusters: {e.message}', e.response)


def addGalaxy(server, definition: dict) -> None:
    try:
        post(server, '/galaxies/add', {'Galaxy': definition})
    except MispOpError as e:
        raise MispOpError(f"Could not create galaxy `{definition.get('name')}`: {e.message}", e.response)
