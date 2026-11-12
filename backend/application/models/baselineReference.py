#!/usr/bin/env python3
"""A reference server: what a baseline could take from one of the user's servers. Its settings come from its last
snapshot; its taxonomies, galaxies and object templates are listed from MISP on request, so that rules can be picked
from what the server has now"""

import asyncio
from typing import Optional

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

# Rule type → the MISP index listing its items
INDEXES = {
    'taxonomy_enabled': mispOps.TAXONOMY_INDEX,
    'galaxy_enabled': mispOps.GALAXY_INDEX,
    'object_template_active': mispOps.OBJECT_TEMPLATE_INDEX,
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


def item(key: str, label: str, enabled: bool, description: str = '', group: str = '') -> dict:
    return {'key': key, 'label': label or key, 'enabled': enabled, 'description': description or '',
            'group': group or ''}


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


BUILDERS = {
    'taxonomy_enabled': taxonomyList,
    'galaxy_enabled': galaxyList,
    'object_template_active': templateList,
}


def listedContent(answers: list) -> dict:
    """Rule type → {items} or {error}, from the decoded answers of the indexes, in `INDEXES` order"""
    content = {}
    for (type, (url, model, what)), data in zip(INDEXES.items(), answers):
        try:
            content[type] = {'items': BUILDERS[type](mispOps.decodedRecords(data, model, what)), 'source': 'live'}
        except mispOps.MispOpError as e:
            content[type] = {'error': e.message}
        except Exception as e:
            content[type] = {'error': f'Could not list the {what}: {e}'}
    return content


def lastKnownContent(snapshot: Optional[dict], reason: str) -> dict:
    """What the last refresh or check listed, for a server that cannot be asked now"""
    state = ((snapshot or {}).get('query_result') or {}).get('baselineState')
    state = state if isinstance(state, dict) else {}
    content = {}
    for type, section in CONTENT_SECTIONS.items():
        items = (state.get(section) or {}).get('items') if isinstance(state.get(section), dict) else None
        if not isinstance(items, dict):
            content[type] = {'error': reason}
            continue
        content[type] = {
            'items': byLabel([item(key, value.get('name') or key, value.get('enabled') is True)
                              for key, value in items.items() if isinstance(value, dict)]),
            'source': 'snapshot',
            'listed_at': state.get('timestamp'),
        }
    return content


async def fetchContent(server) -> list:
    from application.models.utils import asyncFetcher
    return await asyncFetcher(server, [url for url, model, what in INDEXES.values()], timeout=REFERENCE_TIMEOUT)


def referenceForUser(user, server_id: int) -> dict:
    server = Server.query.filter_by(id=server_id, user_id=user.id).first()
    if server is None:
        raise BaselineError('Unknown server', 404)
    snapshot = redisModel.getServerInfo(server.uuid)
    state = ServerState(server, snapshot, redisModel.getServerStatus(server.uuid))
    blocking = blocking_issue(state, Context.for_user(user))

    if not server.authkey:
        content = lastKnownContent(snapshot, 'This server has no API key')
    elif blocking is not None:
        content = lastKnownContent(snapshot, blocking.title)
    else:
        try:
            content = listedContent(asyncio.run(fetchContent(server)))
        except Exception as e:
            content = lastKnownContent(snapshot, f'Could not reach the server: {e}')

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
