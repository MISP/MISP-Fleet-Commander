#!/usr/bin/env python3
"""Baseline drift of a fleet's servers: the content listings rules need (`baselineState` in each snapshot), the
light check that refreshes them, re-evaluation when rules change, and the drift matrix. Evaluation itself lives in
`application.health.drift`, next to the health rule it feeds"""

import asyncio
import time
from typing import Dict, Iterable, List, Optional

from application import redisModel
from application.DBModels import Baseline, BaselineRule, Fleet, Server, db
from application.health import Context
from application.health import drift
from application.health.engine import ServerState, blocking_issue
from application.models import mispOps
from application.models.baselines import BaselineError, galaxyLabel, ownedFleet, serializedRulesOfFleet

# Listing a server's content for a check (each index is one request)
CONTENT_TIMEOUT = 60


def taxonomyItems(records: list) -> dict:
    return {namespace: {'enabled': taxonomy['enabled']}
            for namespace, taxonomy in mispOps.parseTaxonomies(records).items()}


def galaxyItems(records: list) -> dict:
    return {uuid: {'enabled': galaxy['enabled'], 'name': galaxyLabel(galaxy['namespace'], galaxy['name'])}
            for uuid, galaxy in mispOps.parseGalaxies(records).items()}


def templateItems(records: list) -> dict:
    return {uuid: {'enabled': template['active'], 'name': template['name']}
            for uuid, template in mispOps.parseObjectTemplates(records).items()}


def withoutId(items: Dict[str, dict]) -> dict:
    """MISP's local IDs mean nothing to drift"""
    return {key: {field: value for field, value in item.items() if field != 'id'} for key, item in items.items()}


def organisationItems(records: list) -> dict:
    return withoutId(mispOps.parseOrganisations(records))


def sharingGroupItems(groups: Dict[str, dict]) -> dict:
    return withoutId(groups)


def customGalaxyItems(records: list) -> dict:
    """The custom galaxies only: clusters are added for those the rules name"""
    custom = [record for record in records if mispOps.isCustomGalaxy(record)]
    return {uuid: {'name': galaxy['name'], 'namespace': galaxy['namespace'], 'enabled': galaxy['enabled']}
            for uuid, galaxy in mispOps.parseGalaxies(custom).items()}


def recordsOf(index):
    url, model, what = index
    return lambda data: mispOps.decodedRecords(data, model, what)


# Rule type → (the MISP index to list, how to read its decoded answer, how to keep it). Sections are named by
# `drift.CONTENT_SECTIONS`
CONTENT_INDEXES = {
    'taxonomy_enabled': (mispOps.TAXONOMY_INDEX[0], recordsOf(mispOps.TAXONOMY_INDEX), taxonomyItems),
    'galaxy_enabled': (mispOps.GALAXY_INDEX[0], recordsOf(mispOps.GALAXY_INDEX), galaxyItems),
    'object_template_active': (mispOps.OBJECT_TEMPLATE_INDEX[0], recordsOf(mispOps.OBJECT_TEMPLATE_INDEX),
                               templateItems),
    'organisation': (mispOps.ORGANISATION_INDEX[0], recordsOf(mispOps.ORGANISATION_INDEX), organisationItems),
    'sharing_group': (mispOps.SHARING_GROUP_INDEX[0], mispOps.decodedSharingGroups, sharingGroupItems),
    'custom_galaxy': (mispOps.GALAXY_INDEX[0], recordsOf(mispOps.GALAXY_INDEX), customGalaxyItems),
}
assert set(CONTENT_INDEXES) == set(drift.CONTENT_SECTIONS)


class ContentPlan:
    """What a server lists for its fleet's rules: the index of each content type the rules use, and the clusters of
    each custom galaxy a rule names. `urls` are asked once each; `state` reads their decoded answers"""

    def __init__(self, types: Iterable[str], galaxies: Iterable[str] = ()):
        self.types = [type for type in CONTENT_INDEXES if type in set(types)]
        self.galaxies = sorted(set(galaxies)) if 'custom_galaxy' in self.types else []

    def __bool__(self) -> bool:
        return bool(self.types)

    @property
    def urls(self) -> List[str]:
        urls = [CONTENT_INDEXES[type][0] for type in self.types]
        urls += [mispOps.galaxyClustersUrl(uuid) for uuid in self.galaxies]
        return list(dict.fromkeys(urls))

    def state(self, answers: list, now: Optional[int] = None) -> dict:
        """`baselineState` from the decoded answers of `urls`, in the same order. A section that could not be listed
        carries the reason instead of items"""
        byUrl = dict(zip(self.urls, answers))
        state = {'timestamp': int(time.time()) if now is None else now}
        for type in self.types:
            url, decode, build = CONTENT_INDEXES[type]
            section = drift.CONTENT_SECTIONS[type]
            try:
                state[section] = {'items': build(decode(byUrl.get(url)))}
            except mispOps.MispOpError as e:
                state[section] = {'error': e.message}
            except Exception as e:  # A malformed record must not lose the rest of the refresh
                state[section] = {'error': f'Could not list the {drift.CONTENT_NOUNS[section]}: {e}'}
        galaxies = state.get('customGalaxies', {}).get('items')
        for uuid in self.galaxies if isinstance(galaxies, dict) else []:
            if uuid not in galaxies:
                continue
            try:
                clusters = mispOps.decodedGalaxyClusters(byUrl.get(mispOps.galaxyClustersUrl(uuid)))
                galaxies[uuid]['clusters'] = clusters or {}
            except mispOps.MispOpError as e:
                galaxies[uuid]['clusters_error'] = e.message
            except Exception as e:
                galaxies[uuid]['clusters_error'] = f'Could not list the galaxy clusters: {e}'
        return state


def contentPlanOfFleet(fleet_id: Optional[int]) -> ContentPlan:
    if fleet_id is None:
        return ContentPlan([])
    rows = db.session.query(BaselineRule.type, BaselineRule.key).join(Baseline) \
        .filter(Baseline.fleet_id == fleet_id, BaselineRule.type.in_(list(CONTENT_INDEXES))).all()
    return ContentPlan({type for type, key in rows}, [key for type, key in rows if type == 'custom_galaxy'])


def contentTypesOfFleet(fleet_id: Optional[int]) -> List[str]:
    """Rule types of the fleet's baseline that need content listed from the servers, in a fixed order"""
    return contentPlanOfFleet(fleet_id).types


def contentUrls(types: Iterable[str]) -> List[str]:
    return ContentPlan(types).urls


def contentState(types: List[str], answers: list, now: Optional[int] = None) -> dict:
    """`baselineState` for content types that need no cluster listing (see `ContentPlan.state`)"""
    return ContentPlan(types).state(answers, now)


def fillLabels(fleet_id: int, state: Optional[dict]) -> None:
    """Names galaxies and object templates the rules know only by UUID, from what a server listed"""
    if not isinstance(state, dict):
        return
    rules = BaselineRule.query.join(Baseline).filter(
        Baseline.fleet_id == fleet_id, BaselineRule.label == '',
        BaselineRule.type.in_(['galaxy_enabled', 'object_template_active'])).all()
    changed = False
    for rule in rules:
        section = state.get(drift.CONTENT_SECTIONS[rule.type])
        items = section.get('items') if isinstance(section, dict) else None
        name = (items or {}).get(rule.key, {}).get('name')
        if name:
            rule.label = name[:255]
            changed = True
    if changed:
        db.session.commit()


def afterContentFetched(server, state: Optional[dict]) -> None:
    """Never raises: a refresh must not fail because of the baseline"""
    try:
        fillLabels(server.fleet_id, state)
    except Exception as e:
        db.session.rollback()
        print(f'Could not name the baseline rules of fleet {server.fleet_id}: {e}')


# The light check: content listings only, without the rest of a full refresh

async def fetchContentStateAsync(server, plan: ContentPlan) -> dict:
    from application.models.utils import asyncFetcher
    answers = await asyncFetcher(server, plan.urls, timeout=CONTENT_TIMEOUT)
    return plan.state(answers)


def checkServers(servers: List[Server], max_concurrency: int = 10) -> Dict[int, str]:
    """Lists again the content the baseline rules of each server's fleet need, saves it in the snapshot and
    re-evaluates health. `{server_id: outcome}`: `checked`, or why the server was skipped"""
    outcomes, todo = {}, []
    plansByFleet = {}
    for server in servers:
        plan = plansByFleet.setdefault(server.fleet_id, contentPlanOfFleet(server.fleet_id))
        if not plan:
            outcomes[server.id] = 'no content rules'
        elif not server.authkey:
            outcomes[server.id] = 'no API key'
        elif redisModel.getServerInfo(server.uuid) is None:
            outcomes[server.id] = 'never refreshed: a full refresh is needed'
        else:
            todo.append((server, plan))

    async def fetchAll():
        semaphore = asyncio.Semaphore(max(int(max_concurrency), 1))

        async def fetch(server, plan):
            async with semaphore:
                try:
                    return await fetchContentStateAsync(server, plan)
                except Exception as e:
                    print(f'Baseline check of server {server.id} failed: {e}')
                    return None
        return await asyncio.gather(*[fetch(server, plan) for server, plan in todo])

    from application.models.servers import publishHealth, savePartialInfo
    for (server, plan), state in zip(todo, asyncio.run(fetchAll()) if todo else []):
        if state is None:
            outcomes[server.id] = 'failed'
            continue
        savePartialInfo(server, 'baselineState', state)
        afterContentFetched(server, state)
        publishHealth(server)
        outcomes[server.id] = 'checked'
    return outcomes


def enqueueCheck(server_ids: List[int]) -> bool:
    """Hands a check to the workers. False when they cannot be reached"""
    if not server_ids:
        return True
    try:
        from application.workers.tasks import checkBaselineTask
        checkBaselineTask(server_ids)
        return True
    except Exception as e:
        print(f'Could not queue the baseline check of servers {server_ids}: {e}')
        return False


def checkFleet(user, fleet_id: int) -> dict:
    fleet = ownedFleet(user, fleet_id)
    server_ids = [server.id for server in fleet.servers]
    if not contentTypesOfFleet(fleet.id):
        return {'server_ids': [], 'message': 'The baseline has no taxonomy, galaxy, object template, organisation or '
                                             'sharing group rule to check'}
    if not enqueueCheck(server_ids):
        raise BaselineError('The check could not be started: the workers could not be reached', 503)
    return {'server_ids': server_ids}


def missingContent(server, plan: ContentPlan) -> bool:
    """Whether the server never listed a section the rules need, or the clusters of a custom galaxy it has"""
    snapshot = redisModel.getServerInfo(server.uuid)
    if snapshot is None:
        return False  # Its first full refresh will list the content
    state = (snapshot.get('query_result') or {}).get('baselineState')
    state = state if isinstance(state, dict) else {}
    if any(drift.CONTENT_SECTIONS[type] not in state for type in plan.types):
        return True
    galaxies = (state.get('customGalaxies') or {}).get('items') if isinstance(state.get('customGalaxies'), dict) \
        else None
    galaxies = galaxies if isinstance(galaxies, dict) else {}
    return any(isinstance(galaxies.get(uuid), dict) and 'clusters' not in galaxies[uuid]
               and 'clusters_error' not in galaxies[uuid] for uuid in plan.galaxies)


def rulesChanged(fleet: Fleet) -> None:
    """Re-evaluates the fleet's servers and sends their health to the owner. Servers that never listed the content
    a new rule needs are checked in the background. Never raises: the rules are saved already"""
    try:
        from application.models.health import publishServerHealth
        plan = contentPlanOfFleet(fleet.id)
        servers = list(fleet.servers)
        missing = [server.id for server in servers if plan and server.authkey and missingContent(server, plan)]
        enqueueCheck(missing)
        for server in servers:
            publishServerHealth(server)
    except Exception as e:
        print(f'Could not re-evaluate the baseline of fleet {fleet.id}: {e}')


# Drift matrix

def driftForUser(user, fleet_id: int) -> dict:
    """Every rule against every server of the fleet. A server that cannot be reached keeps its last known values,
    but its results are `unknown`: they may no longer be true"""
    fleet = ownedFleet(user, fleet_id)
    rules = serializedRulesOfFleet(fleet.id)
    ctx = Context.for_user(user)
    totals = {state: 0 for state in drift.STATES}
    servers = []
    for server in sorted(fleet.servers, key=lambda s: (s.name.lower(), s.id)):
        snapshot = redisModel.getServerInfo(server.uuid)
        state = ServerState(server, snapshot, redisModel.getServerStatus(server.uuid))
        blocking = blocking_issue(state, ctx)
        results, driftCount = {}, 0
        for result in drift.evaluate(rules, state):
            cell = {'state': result.state, 'actual': result.actual, 'reason': result.reason}
            if blocking is not None and result.state != drift.UNKNOWN:
                cell.update(state=drift.UNKNOWN, reason=f'{blocking.title}: last known value', stale=True)
            totals[cell['state']] += 1
            driftCount += cell['state'] == drift.DRIFT
            results[str(result.rule_id)] = cell
        content = state.query_result.get('baselineState')
        servers.append({
            'id': server.id,
            'name': server.name,
            'url': server.url,
            'refreshed_at': (state.snapshot or {}).get('timestamp'),
            'content_checked_at': content.get('timestamp') if isinstance(content, dict) else None,
            'unavailable': blocking.title if blocking is not None else None,
            'drift': driftCount,
            'results': results,
        })
    return {'fleet_id': fleet.id, 'evaluated_at': ctx.now, 'rules': rules, 'servers': servers, 'totals': totals}
