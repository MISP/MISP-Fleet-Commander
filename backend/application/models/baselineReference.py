#!/usr/bin/env python3
"""A reference server: what a baseline could take from one of the user's servers. Its settings come from its last
snapshot; its taxonomies, galaxies, object templates, organisations, sharing groups and custom galaxies (with their
clusters) are listed from MISP on request, so that rules can be picked from what the server has now"""

import asyncio
from typing import Any, Dict, List, Optional

from application import redisModel
from application.DBModels import Server
from application.health import Context
from application.health.drift import CONTENT_SECTIONS, currentVersion
from application.health.engine import ServerState, blocking_issue
from application.models import mispOps
from application.models.baselines import SETTING_NAME, BaselineError, galaxyLabel, isServerSpecificSetting
from application.models.jobs import isSensitiveSetting

# The user waits for the listing: shorter than a background check
REFERENCE_TIMEOUT = 30
# Each custom galaxy's clusters are one more request
MAX_CUSTOM_GALAXIES = 100

# Rule type → the MISP index listing its items
INDEXES = {
    'taxonomy_enabled': mispOps.TAXONOMY_INDEX,
    'galaxy_enabled': mispOps.GALAXY_INDEX,
    'object_template_active': mispOps.OBJECT_TEMPLATE_INDEX,
    'organisation': mispOps.ORGANISATION_INDEX,
    'sharing_group': mispOps.SHARING_GROUP_INDEX,
    'custom_galaxy': mispOps.GALAXY_INDEX,
}
assert set(INDEXES) == set(CONTENT_SECTIONS)


def settingItems(snapshot: Optional[dict]) -> list:
    """Settings a rule may name, by name. Secrets are left out: a baseline refuses them"""
    items = []
    for name, entry in sorted(mispOps.snapshotSettings(snapshot).items()):
        if not SETTING_NAME.match(name) or isSensitiveSetting(name) or entry.get('redacted'):
            continue
        options = entry.get('options')
        items.append({
            'name': name,
            'value': entry.get('value'),
            'type': entry.get('type'),
            'tab': entry.get('tab') or name.split('.', 1)[0],
            'level': entry.get('level'),
            'options': options if isinstance(options, (list, dict)) and options else None,
            'server_specific': isServerSpecificSetting(name),
            'cli_only': bool(entry.get('cli_only')),
        })
    return items


def item(key: str, label: str, enabled: bool, description: str = '', group: str = '', **extra) -> dict:
    """`extra`: for organisations, sharing groups and custom galaxies, `expected` (what a rule taken from the item
    expects) and what the list shows of it"""
    return {'key': key, 'label': label or key, 'enabled': enabled, 'description': description or '',
            'group': group or '', **extra}


def byLabel(items: list) -> list:
    return sorted(items, key=lambda entry: (entry['label'].lower(), entry['key']))


def taxonomyList(records: list) -> list:
    descriptions = {record.get('namespace'): record.get('description') for record in records}
    return byLabel([item(namespace, namespace, taxonomy['enabled'], descriptions.get(namespace))
                    for namespace, taxonomy in mispOps.parseTaxonomies(records).items()])


def galaxyList(records: list) -> list:
    descriptions = {mispOps.uuidKey(record.get('uuid') or ''): record.get('description') for record in records}
    return byLabel([item(uuid, galaxyLabel(galaxy['namespace'], galaxy['name']), galaxy['enabled'],
                         descriptions.get(uuid), galaxy['namespace'])
                    for uuid, galaxy in mispOps.parseGalaxies(records).items()])


def templateList(records: list) -> list:
    descriptions = {mispOps.uuidKey(record.get('uuid') or ''): record.get('description') for record in records}
    return byLabel([item(uuid, template['name'], template['active'], descriptions.get(uuid),
                         template['meta_category'])
                    for uuid, template in mispOps.parseObjectTemplates(records).items()])


# Organisations, sharing groups and custom galaxies, from their items in `baselineState` form (see
# `application.health.drift`): the live listing and the last known one read the same

def organisationList(items: dict) -> list:
    rows = []
    for uuid, org in items.items():
        expected = {'name': org.get('name') or ''}
        for field in ('type', 'nationality', 'sector'):
            if org.get(field):
                expected[field] = org[field]
        # Local or external is left unchecked: an organisation is local on its own server only
        rows.append(item(uuid, org.get('name'), True,
                         ' · '.join(org[field] for field in ('type', 'nationality', 'sector') if org.get(field)),
                         'Local' if org.get('local') else 'External', local=org.get('local') is True,
                         expected=expected))
    return byLabel(rows)


def sharingGroupList(items: dict) -> list:
    rows = []
    for uuid, sg in items.items():
        members = sg.get('members') if isinstance(sg.get('members'), dict) else {}
        expected = {
            'name': sg.get('name') or '',
            'releasability': sg.get('releasability') or '',
            'description': sg.get('description') or '',
            'active': sg.get('active') is True,
            'roaming': sg.get('roaming') is True,
            'members': [{'uuid': orgUuid, 'name': member.get('name') or orgUuid, 'extend': member.get('extend') is True}
                        for orgUuid, member in members.items()],
        }
        rows.append(item(uuid, sg.get('name'), sg.get('active') is True, sg.get('description') or sg.get('releasability'),
                         members=len(members), expected=expected))
    return byLabel(rows)


def customGalaxyList(items: dict, server_id: int) -> list:
    rows = []
    for uuid, galaxy in items.items():
        label = galaxyLabel(galaxy.get('namespace'), galaxy.get('name') or uuid)
        extra = {}
        clusters = galaxy.get('clusters')
        if isinstance(clusters, dict):
            extra = {'clusters': len(clusters), 'expected': {
                'name': galaxy.get('name') or '', 'namespace': galaxy.get('namespace') or '',
                'source_server_id': server_id, 'clusters': clusters}}
        else:
            # Without its clusters no rule can be taken from it
            extra = {'unavailable': galaxy.get('clusters_error') or 'Its clusters were not listed'}
        rows.append(item(uuid, label, galaxy.get('enabled') is True, '', galaxy.get('namespace'), **extra))
    return byLabel(rows)


STRUCTURED_LISTS = {
    'organisation': lambda items, server: organisationList(items),
    'sharing_group': lambda items, server: sharingGroupList(items),
    'custom_galaxy': lambda items, server: customGalaxyList(items, server.id),
}

BUILDERS = {
    'taxonomy_enabled': taxonomyList,
    'galaxy_enabled': galaxyList,
    'object_template_active': templateList,
}


def listedContent(answers: Dict[str, Any], server) -> dict:
    """Rule type → {items} or {error}, from the decoded answers of the indexes and of the custom galaxies' clusters,
    by URL"""
    from application.models.baselineDrift import ContentPlan
    content = {}
    for type, (url, model, what) in BUILDERS_INDEXES.items():
        try:
            records = mispOps.decodedRecords(answers.get(url), model, what)
            content[type] = {'items': BUILDERS[type](records), 'source': 'live'}
        except mispOps.MispOpError as e:
            content[type] = {'error': e.message}
        except Exception as e:
            content[type] = {'error': f'Could not list the {what}: {e}'}
    plan = ContentPlan(STRUCTURED_LISTS, customGalaxyUuids(answers))
    state = plan.state([answers.get(url) for url in plan.urls])
    for type, build in STRUCTURED_LISTS.items():
        content[type] = structuredSection(type, state, server, build)
        if 'items' in content[type]:
            content[type]['source'] = 'live'
    return content


def structuredSection(type: str, state: dict, server, build) -> dict:
    section = state.get(CONTENT_SECTIONS[type])
    if not isinstance(section, dict) or not isinstance(section.get('items'), dict):
        return {'error': (section or {}).get('error') or 'Not listed'}
    return {'items': build(section['items'], server)}


def customGalaxyUuids(answers: Dict[str, Any]) -> List[str]:
    """The custom galaxies of the galaxy listing, whose clusters are listed too"""
    data = answers.get(mispOps.GALAXY_INDEX[0])
    try:
        records = mispOps.decodedRecords(data, 'Galaxy', 'galaxies')
    except mispOps.MispOpError:
        return []
    custom = [record for record in records if mispOps.isCustomGalaxy(record) and record.get('uuid')]
    return [mispOps.uuidKey(record['uuid']) for record in custom][:MAX_CUSTOM_GALAXIES]


def lastKnownContent(snapshot: Optional[dict], reason: str, server) -> dict:
    """What the last refresh or check listed, for a server that cannot be asked now"""
    state = ((snapshot or {}).get('query_result') or {}).get('baselineState')
    state = state if isinstance(state, dict) else {}
    content = {}
    for type, section in CONTENT_SECTIONS.items():
        items = (state.get(section) or {}).get('items') if isinstance(state.get(section), dict) else None
        if not isinstance(items, dict):
            content[type] = {'error': reason}
            continue
        if type in STRUCTURED_LISTS:
            rows = STRUCTURED_LISTS[type](items, server)
        else:
            rows = byLabel([item(key, value.get('name') or key, value.get('enabled') is True)
                            for key, value in items.items() if isinstance(value, dict)])
        content[type] = {'items': rows, 'source': 'snapshot', 'listed_at': state.get('timestamp')}
    return content


# The indexes the reference lists itself (the others are read through `ContentPlan`)
BUILDERS_INDEXES = {type: INDEXES[type] for type in BUILDERS}


async def fetchContent(server) -> Dict[str, Any]:
    """Decoded answers by URL: the indexes, then the clusters of each custom galaxy"""
    from application.models.utils import asyncFetcher
    urls = list(dict.fromkeys(url for url, model, what in INDEXES.values()))
    answers = dict(zip(urls, await asyncFetcher(server, urls, timeout=REFERENCE_TIMEOUT)))
    clusterUrls = [mispOps.galaxyClustersUrl(uuid) for uuid in customGalaxyUuids(answers)]
    if clusterUrls:
        answers.update(zip(clusterUrls, await asyncFetcher(server, clusterUrls, timeout=REFERENCE_TIMEOUT)))
    return answers


def referenceForUser(user, server_id: int) -> dict:
    server = Server.query.filter_by(id=server_id, user_id=user.id).first()
    if server is None:
        raise BaselineError('Unknown server', 404)
    snapshot = redisModel.getServerInfo(server.uuid)
    state = ServerState(server, snapshot, redisModel.getServerStatus(server.uuid))
    blocking = blocking_issue(state, Context.for_user(user))

    if not server.authkey:
        content = lastKnownContent(snapshot, 'This server has no API key', server)
    elif blocking is not None:
        content = lastKnownContent(snapshot, blocking.title, server)
    else:
        try:
            content = listedContent(asyncio.run(fetchContent(server)), server)
        except Exception as e:
            content = lastKnownContent(snapshot, f'Could not reach the server: {e}', server)

    settings = settingItems(snapshot)
    if snapshot is None:
        settingsError = 'This server was never refreshed: refresh it first'
    elif not mispOps.snapshotSettings(snapshot):
        settingsError = 'Its last refresh got no settings from MISP'
    else:
        settingsError = None
    return {
        'server': {'id': server.id, 'name': server.name, 'url': server.url, 'fleet_id': server.fleet_id},
        'version': currentVersion(state),
        'refreshed_at': (snapshot or {}).get('timestamp'),
        'unavailable': blocking.title if blocking is not None else None,
        'settings': settings,
        'settings_error': settingsError,
        'content': content,
    }
