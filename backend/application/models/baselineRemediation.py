#!/usr/bin/env python3
"""Fixing baseline drift. A preview lists what a fix would change (`server · rule · current → expected`) and what
must be done by hand; confirming starts a `baseline_remediation` job, one unit per server applying that server's
drifting rules in order. Each unit reads every value back from MISP, updates the server's snapshot with what it
read and publishes the server's health, so the drift matrix and the issues follow without a refresh"""

import time
from typing import Any, Dict, List, Optional

from application import redisModel
from application.DBModels import BaselineRule, Server, db
from application.health import Context
from application.health import drift
from application.health.engine import ServerState, blocking_issue
from application.models import mispOps
from application.models.baselines import BaselineError, ownedFleet, serializedRulesOfFleet
from application.models.jobs import UnitResult, redactValue

APPLY = 'apply'
MANUAL = 'manual'
MAX_ITEMS = 5000

# Unit outcomes, per rule
FIXED = 'fixed'
ALREADY = 'already'
FAILED = 'error'


# Preview

def manualReason(baselineRule: dict, result, entries: Dict[str, dict], server=None) -> Optional[str]:
    """Why a drifting rule cannot be fixed from here, or None"""
    if baselineRule['type'] == 'version_min':
        return 'Upgrade MISP on this server'
    if baselineRule['type'] == 'setting':
        entry = entries.get(baselineRule['key']) or {}
        if entry.get('cli_only') or entry.get('editable') is False:
            return 'MISP only lets this setting change from its command line'
        return None
    if baselineRule['type'] == 'custom_galaxy':
        return galaxySourceProblem(baselineRule, result, server)
    if baselineRule['type'] in drift.STRUCTURED_TYPES:
        return None  # Created when missing
    if result.actual is None:
        return 'Not on this server: update its taxonomies, galaxies or object templates in MISP first'
    return None


def galaxySourceProblem(baselineRule: dict, result, server) -> Optional[str]:
    """A custom galaxy that is missing clusters is copied from the server the rule names: it must still exist, and
    it cannot be the drifting server itself. Enabling it needs no source"""
    actual = result.actual
    if isinstance(actual, dict) and not actual.get('missing') and not actual.get('older'):
        return None
    source = sourceServer(baselineRule['expected'], server)
    if source is None:
        return 'The server this galaxy is copied from no longer exists: take the rule again from another server'
    if server is not None and source.id == server.id:
        return 'This is the server the galaxy is copied from: add its clusters in MISP'
    return None


def sourceServer(expected: Any, server) -> Optional[Server]:
    """The server a custom galaxy is copied from, when it still exists and belongs to the drifting server's owner"""
    source_id = expected.get('source_server_id') if isinstance(expected, dict) else None
    if isinstance(source_id, bool) or not isinstance(source_id, int):
        return None
    source = db.session.get(Server, source_id)
    if source is None or (server is not None and source.user_id != server.user_id):
        return None
    return source


def previewForUser(user, fleet_id: int, server_ids: Any = None, rule_ids: Any = None, pairs: Any = None) -> dict:
    """The drifting rules in scope, per server: the whole fleet, some servers, some rules, or exact
    `[{server_id, rule_id}]` pairs. Servers that cannot be reached are listed apart: their values are not known"""
    fleet = ownedFleet(user, fleet_id)
    serverFilter = idSet(server_ids, 'server_ids')
    ruleFilter = idSet(rule_ids, 'rule_ids')
    pairFilter = pairSet(pairs)
    rules = serializedRulesOfFleet(fleet.id)
    if ruleFilter is not None:
        rules = [rule for rule in rules if rule['id'] in ruleFilter]
    if pairFilter is not None:
        wanted = {rule_id for _, rule_id in pairFilter}
        rules = [rule for rule in rules if rule['id'] in wanted]
    rulesById = {rule['id']: rule for rule in rules}
    ctx = Context.for_user(user)

    servers, excluded = [], []
    counts = {APPLY: 0, MANUAL: 0}
    for server in sorted(fleet.servers, key=lambda s: (s.name.lower(), s.id)):
        if serverFilter is not None and server.id not in serverFilter:
            continue
        if pairFilter is not None and not any(server_id == server.id for server_id, _ in pairFilter):
            continue
        snapshot = redisModel.getServerInfo(server.uuid)
        state = ServerState(server, snapshot, redisModel.getServerStatus(server.uuid))
        blocking = blocking_issue(state, ctx)
        if blocking is not None:
            excluded.append({'id': server.id, 'name': server.name, 'reason': blocking.title})
            continue
        if not server.authkey:
            excluded.append({'id': server.id, 'name': server.name, 'reason': 'No API key'})
            continue
        entries = mispOps.snapshotSettings(snapshot)
        items = []
        for result in drift.evaluate(rules, state):
            if result.state != drift.DRIFT:
                continue
            if pairFilter is not None and (server.id, result.rule_id) not in pairFilter:
                continue
            rule = rulesById[result.rule_id]
            reason = manualReason(rule, result, entries, server)
            action = MANUAL if reason else APPLY
            counts[action] += 1
            items.append({
                'rule_id': rule['id'],
                'type': rule['type'],
                'key': rule['key'],
                'label': rule['label'],
                'severity': rule['severity'],
                'comparator': rule['comparator'],
                'expected': compactExpected(rule),
                'current': result.actual,
                # What differs, for organisations, sharing groups and custom galaxies
                'difference': result.reason if rule['type'] in drift.STRUCTURED_TYPES else '',
                'action': action,
                'reason': reason or '',
            })
        if items:
            # The order the fix applies them in
            items.sort(key=lambda item: TYPE_ORDER.get(item['type'], 2))
            servers.append({'id': server.id, 'name': server.name, 'items': items})
    counts['servers'] = sum(1 for server in servers if any(item['action'] == APPLY for item in server['items']))
    return {'fleet_id': fleet.id, 'servers': servers, 'excluded': excluded, 'counts': counts}


def compactExpected(rule: dict) -> Any:
    """What the preview and the job keep of the expected value: a sharing group's members and a galaxy's clusters
    are read from the rule when the fix runs"""
    if rule['type'] not in drift.STRUCTURED_TYPES:
        return rule['expected']
    expected = rule['expected'] or {}
    compact = {'name': expected.get('name')}
    if rule['type'] == 'sharing_group':
        compact['members'] = len(expected.get('members') or [])
    elif rule['type'] == 'custom_galaxy':
        compact['clusters'] = len(expected.get('clusters') or {})
    return compact


def idSet(value: Any, field: str) -> Optional[set]:
    if value is None:
        return None
    if not isinstance(value, list) or any(isinstance(id, bool) or not isinstance(id, int) for id in value):
        raise BaselineError(f'`{field}` must be a list of IDs', field=field)
    return set(value)


def pairSet(value: Any) -> Optional[set]:
    if value is None:
        return None
    if not isinstance(value, list) or len(value) == 0 or len(value) > MAX_ITEMS:
        raise BaselineError(f'`items` must be a list of 1 to {MAX_ITEMS} {{server_id, rule_id}}', field='items')
    pairs = set()
    for item in value:
        server_id = item.get('server_id') if isinstance(item, dict) else None
        rule_id = item.get('rule_id') if isinstance(item, dict) else None
        if any(isinstance(id, bool) or not isinstance(id, int) for id in (server_id, rule_id)):
            raise BaselineError('Each item needs a `server_id` and a `rule_id`', field='items')
        pairs.add((server_id, rule_id))
    return pairs


# Starting the job

def jobTitle(plan: dict, applied: List[dict]) -> str:
    servers = [server for server in plan['servers'] if any(item['action'] == APPLY for item in server['items'])]
    if len(applied) == 1:
        item = applied[0]
        return f"Fix {item['label'] or item['key'] or 'the MISP version'} on {servers[0]['name']}"
    where = servers[0]['name'] if len(servers) == 1 else f'{len(servers)} servers'
    return f'Fix {len(applied)} baseline values on {where}'


def startForUser(user, fleet_id: int, pairs: Any) -> 'Job':
    """Fixes the given `[{server_id, rule_id}]`, as far as they still drift and can be fixed from here. The plan is
    computed again: what the user previewed may have changed since"""
    from application.models import jobs as jobModel
    from application.models import userJobs
    if pairs is None:
        raise BaselineError('`items` is required', field='items')
    plan = previewForUser(user, fleet_id, pairs=pairs)
    perServer, applied = {}, []
    for server in plan['servers']:
        todo = [item for item in server['items'] if item['action'] == APPLY]
        if todo:
            perServer[str(server['id'])] = [
                {key: item[key] for key in ('rule_id', 'type', 'key', 'label', 'comparator', 'expected')}
                for item in todo]
            applied.extend(todo)
    if not applied:
        raise BaselineError('Nothing left to fix: these servers no longer drift, or only by hand', 409)
    fleet = ownedFleet(user, fleet_id)
    servers = Server.query.filter(Server.id.in_([int(id) for id in perServer]), Server.user_id == user.id).all()
    servers.sort(key=lambda s: (s.name.lower(), s.id))
    job = jobModel.create(user, 'baseline_remediation', servers,
                          params={'fleet_id': fleet.id, 'servers': perServer},
                          title=jobTitle(plan, applied), fleet=fleet)
    try:
        return userJobs.enqueue(job)
    except userJobs.JobError as e:
        raise BaselineError(e.message, e.status)


# The unit: one server

TOGGLE_INDEXES = {
    'taxonomy_enabled': mispOps.TAXONOMY_INDEX,
    'galaxy_enabled': mispOps.GALAXY_INDEX,
    'object_template_active': mispOps.OBJECT_TEMPLATE_INDEX,
}
# Organisations first: a sharing group's members may be among them
TYPE_ORDER = {'organisation': 0, 'sharing_group': 1}


class ContentCache:
    """Each content index is listed once before the writes and once after, to check them. A custom galaxy's clusters
    are listed when asked for"""

    def __init__(self, server):
        self.server = server
        self.parsed = {}
        self.clusters = {}

    def get(self, type: str) -> Dict[str, dict]:
        if type not in self.parsed:
            if type in TOGGLE_INDEXES:
                self.parsed[type] = parsedContent(type, mispOps.listing(self.server, *TOGGLE_INDEXES[type]))
            elif type == 'organisation':
                self.parsed[type] = mispOps.organisations(self.server)
            elif type == 'sharing_group':
                self.parsed[type] = mispOps.sharingGroups(self.server)
            else:
                galaxies = mispOps.listing(self.server, *mispOps.GALAXY_INDEX)
                self.parsed[type] = mispOps.parseGalaxies([g for g in galaxies if mispOps.isCustomGalaxy(g)])
        return self.parsed[type]

    def galaxyClusters(self, uuid: str) -> Optional[Dict[str, int]]:
        if uuid not in self.clusters:
            self.clusters[uuid] = mispOps.galaxyClusters(self.server, uuid)
        return self.clusters[uuid]

    def forget(self, type: str) -> None:
        self.parsed.pop(type, None)
        if type == 'custom_galaxy':
            self.clusters = {}

    def section(self, type: str) -> dict:
        """The items of the type the way `baselineState` keeps them"""
        if type in TOGGLE_INDEXES:
            return {key: {'enabled': value['enabled']} for key, value in self.get(type).items()}
        items = {key: {field: value for field, value in item.items() if field != 'id'}
                 for key, item in self.get(type).items()}
        if type == 'custom_galaxy':
            items = {key: {'name': item['name'], 'namespace': item['namespace'], 'enabled': item['enabled']}
                     for key, item in items.items()}
            for uuid, clusters in self.clusters.items():
                if uuid in items:
                    items[uuid]['clusters'] = clusters or {}
        return items


def parsedContent(type: str, records: list) -> Dict[str, dict]:
    """key → {id, enabled} for any content type"""
    if type == 'taxonomy_enabled':
        return mispOps.parseTaxonomies(records)
    if type == 'galaxy_enabled':
        return mispOps.parseGalaxies(records)
    return {uuid: {**template, 'enabled': template['active']}
            for uuid, template in mispOps.parseObjectTemplates(records).items()}


def judged(item: dict, cache: ContentCache) -> drift.RuleResult:
    """The rule of an organisation, sharing group or custom galaxy against what the cache listed"""
    type, key = item['type'], item['key']
    if type == 'custom_galaxy' and key in cache.get(type):
        cache.galaxyClusters(key)
    content = {drift.CONTENT_SECTIONS[type]: {'items': cache.section(type)}}
    return drift.evaluateStructured({'id': item.get('rule_id'), 'type': type, 'key': key,
                                     'expected': item['expected']}, content)


def applyOrganisation(server, item: dict, cache: ContentCache) -> dict:
    key, expected = item['key'], item['expected']
    found = cache.get('organisation').get(key)
    if found is None:
        fields = {field: expected[field] for field in mispOps.ORGANISATION_FIELDS if field in expected}
        mispOps.addOrganisation(server, key, fields, expected.get('local') is True)
        return {'status': FIXED, 'before': None}
    before = judged(item, cache)
    if before.state == drift.MATCH:
        return {'status': ALREADY, 'before': before.actual}
    changes = {field: expected[field] for field in mispOps.ORGANISATION_FIELDS
               if field in expected and found.get(field) != expected[field]}
    if 'local' in expected and found.get('local') != expected['local']:
        changes['local'] = expected['local']
    mispOps.editOrganisation(server, found['id'], changes)
    return {'status': FIXED, 'before': before.actual}


def applySharingGroup(server, item: dict, cache: ContentCache) -> dict:
    """A missing group is created whole. An existing one gets its missing members and the attributes the rule
    checks: members the rule does not list stay"""
    key, expected = item['key'], item['expected']
    found = cache.get('sharing_group').get(key)
    members = expected.get('members') or []
    payload = {'uuid': key, 'name': expected['name']}
    if found is None:
        payload.update(releasability=expected.get('releasability') or '', description=expected.get('description') or '',
                       active=expected.get('active', True), roaming=expected.get('roaming') is True)
        before = None
    else:
        before = judged(item, cache)
        if before.state == drift.MATCH:
            return {'status': ALREADY, 'before': before.actual}
        before = before.actual
        for field in ('releasability', 'description'):
            if expected.get(field):
                payload[field] = expected[field]
        if 'active' in expected:
            payload['active'] = expected['active']
        members = [member for member in members if member['uuid'] not in found['members']]
    payload['SharingGroupOrg'] = [{'extend': member.get('extend') is True,
                                   'Organisation': {'uuid': member['uuid'], 'name': member['name']}}
                                  for member in members]
    mispOps.captureSharingGroup(server, payload)
    return {'status': FIXED, 'before': before}


def applyCustomGalaxy(server, item: dict, cache: ContentCache) -> dict:
    """Missing or older clusters are imported from the server the rule names (the galaxy comes with them), then the
    galaxy is enabled"""
    key, expected = item['key'], item['expected']
    before = judged(item, cache)
    if before.state == drift.MATCH:
        return {'status': ALREADY, 'before': before.actual}
    actual = before.actual
    if actual is None or actual.get('missing') or actual.get('older'):
        source = sourceServer(expected, server)
        if source is None:
            raise mispOps.MispOpError('The server this galaxy is copied from no longer exists')
        if source.id == server.id:
            raise mispOps.MispOpError('This is the server the galaxy is copied from: add its clusters in MISP')
        sourceGalaxy = mispOps.galaxies(source).get(key)
        if sourceGalaxy is None:
            raise mispOps.MispOpError(f'{source.name}, which the galaxy is copied from, no longer has it')
        clusters = mispOps.exportGalaxyClusters(source, sourceGalaxy['id'])
        if clusters:
            mispOps.importGalaxyClusters(server, clusters)
        elif actual is None:
            mispOps.addGalaxy(server, mispOps.galaxyDefinition(source, sourceGalaxy['id']))
        cache.forget('custom_galaxy')
    found = cache.get('custom_galaxy').get(key)
    if found is not None and not found['enabled']:
        mispOps.setGalaxyEnabled(server, found['id'], True)
    return {'status': FIXED, 'before': actual}


STRUCTURED_APPLY = {
    'organisation': applyOrganisation,
    'sharing_group': applySharingGroup,
    'custom_galaxy': applyCustomGalaxy,
}


def fullItems(items: List[dict], fleet_id: Any) -> List[dict]:
    """The job keeps only the names of organisations, sharing groups and custom galaxies: their whole description is
    read from the rule, which must still be in the fleet's baseline"""
    full = []
    for item in items:
        if item.get('type') in drift.STRUCTURED_TYPES:
            rule = db.session.get(BaselineRule, item.get('rule_id')) if isinstance(item.get('rule_id'), int) else None
            if rule is None or rule.baseline.fleet_id != fleet_id or rule.type != item['type'] or rule.key != item['key']:
                item = {**item, 'missing_rule': True}
            else:
                item = {**item, 'compact': item.get('expected'), 'expected': rule.expected}
        full.append(item)
    return sorted(full, key=lambda item: TYPE_ORDER.get(item.get('type'), 2))


def applySetting(server, item: dict) -> dict:
    key, expected, comparator = item['key'], item['expected'], item.get('comparator') or 'eq'
    before = mispOps.getSetting(server, key)
    if drift.compare(comparator, expected, before):
        return {'status': ALREADY, 'before': before, 'after': before}
    mispOps.editSetting(server, key, '' if expected is None else expected)
    after = mispOps.getSetting(server, key)
    if drift.compare(comparator, expected, after):
        return {'status': FIXED, 'before': before, 'after': after}
    return {'status': FAILED, 'before': before, 'after': after,
            'message': f'MISP accepted the change but still reports {describeValue(after)}'}


def applyContent(server, item: dict, cache: ContentCache) -> dict:
    type, key, expected = item['type'], item['key'], item['expected'] is not False
    found = cache.get(type).get(key)
    if found is None:
        return {'status': FAILED, 'before': None, 'message': 'Not on this server'}
    before = found['enabled']
    if before == expected:
        return {'status': ALREADY, 'before': before, 'after': before}
    if type == 'taxonomy_enabled':
        mispOps.setTaxonomyEnabled(server, found['id'], expected)
    elif type == 'galaxy_enabled':
        mispOps.setGalaxyEnabled(server, found['id'], expected)
    else:
        mispOps.toggleObjectTemplate(server, found['id'])
    return {'status': FIXED, 'before': before}


def describeValue(value: Any) -> str:
    if value is None or value == '':
        return 'an empty value'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return f'`{value}`'


def applyItems(server, items: List[dict], fleet_id: Any = None) -> List[dict]:
    """Applies each rule in order (organisations, then sharing groups, then the rest), then checks the content ones
    against a fresh listing"""
    cache = ContentCache(server)
    outcomes, applied = [], {}
    for item in fullItems(items, fleet_id):
        outcome = {'rule_id': item.get('rule_id'), 'type': item.get('type'), 'key': item.get('key'),
                   'label': item.get('label') or '', 'expected': item.get('compact', item.get('expected'))}
        try:
            if item.get('missing_rule'):
                outcome.update(status=FAILED, message='The rule was removed from the baseline')
            elif item.get('type') == 'setting':
                outcome.update(applySetting(server, item))
            elif item.get('type') in STRUCTURED_APPLY:
                outcome.update(STRUCTURED_APPLY[item['type']](server, item, cache))
            elif item.get('type') in drift.CONTENT_SECTIONS:
                outcome.update(applyContent(server, item, cache))
            else:
                outcome.update(status=FAILED, message='This rule cannot be fixed from here')
        except mispOps.MispOpError as e:
            outcome.update(status=FAILED, message=e.message)
        except Exception as e:
            outcome.update(status=FAILED, message=f'Unexpected error: {e}')
        outcomes.append(outcome)
        applied[id(outcome)] = item

    touched = {o['type'] for o in outcomes if o['type'] in drift.CONTENT_SECTIONS and o['status'] == FIXED}
    fresh = ContentCache(server)
    for outcome in outcomes:
        if outcome['type'] not in touched or outcome['status'] != FIXED:
            continue
        try:
            if outcome['type'] in drift.STRUCTURED_TYPES:
                result = judged(applied[id(outcome)], fresh)
                outcome['after'] = result.actual
                if result.state != drift.MATCH:
                    outcome.update(status=FAILED, message=f'MISP accepted the change, but: {result.reason or "unknown"}')
                continue
            after = fresh.get(outcome['type']).get(outcome['key'])
        except mispOps.MispOpError as e:
            outcome.update(status=FAILED, message=f'Changed, but could not be checked: {e.message}')
            continue
        outcome['after'] = after['enabled'] if after else None
        if after is None or after['enabled'] != (outcome['expected'] is not False):
            outcome.update(status=FAILED, message='MISP accepted the change but the item did not change')
    return outcomes, fresh


def updateSnapshot(server, outcomes: List[dict], fresh: ContentCache) -> None:
    """What the unit read from MISP replaces the snapshot's values, so drift is evaluated on it at once"""
    snapshot = redisModel.getServerInfo(server.uuid)
    if snapshot is None:
        return
    entries = mispOps.snapshotSettings(snapshot)
    for outcome in outcomes:
        if outcome['type'] == 'setting' and 'after' in outcome and outcome['key'] in entries:
            entries[outcome['key']]['value'] = outcome['after']
    if fresh.parsed:
        state = snapshot['query_result'].get('baselineState')
        state = state if isinstance(state, dict) else {}
        for type in list(fresh.parsed):
            section = drift.CONTENT_SECTIONS[type]
            known = state.get(section, {}).get('items') if isinstance(state.get(section), dict) else None
            known = known if isinstance(known, dict) else {}
            items = fresh.section(type)
            if type in TOGGLE_INDEXES:
                # Names come from the last listing; states from this one
                items = {key: {**known.get(key, {}), 'enabled': value['enabled']} for key, value in items.items()}
            elif type == 'custom_galaxy':
                # Clusters of the galaxies not listed again stay as last known
                for key, value in items.items():
                    if 'clusters' not in value and isinstance(known.get(key), dict):
                        for field in ('clusters', 'clusters_error'):
                            if field in known[key]:
                                value[field] = known[key][field]
            state[section] = {'items': items}
        state['timestamp'] = int(time.time())
        snapshot['query_result']['baselineState'] = state
    redisModel.saveServerInfo(server.uuid, snapshot)


def unitSummary(outcomes: List[dict]) -> str:
    fixed = sum(1 for o in outcomes if o['status'] == FIXED)
    already = sum(1 for o in outcomes if o['status'] == ALREADY)
    failed = [o for o in outcomes if o['status'] == FAILED]
    parts = []
    if fixed:
        parts.append(f'{fixed} fixed')
    if already:
        parts.append(f'{already} already as expected')
    if failed:
        first = failed[0]
        parts.append(f"{len(failed)} failed ({first['label'] or first['key']}: {first.get('message', '')})")
    return ', '.join(parts) or 'Nothing to do'


def remediationUnit(server, params: dict) -> UnitResult:
    items = ((params or {}).get('servers') or {}).get(str(server.id)) or []
    if not items:
        return UnitResult(False, skipped=True, summary='Nothing to fix on this server')
    outcomes, fresh = applyItems(server, items, (params or {}).get('fleet_id'))
    try:
        updateSnapshot(server, outcomes, fresh)
    except Exception as e:
        print(f'Could not update the snapshot of server {server.id} after fixing its drift: {e}')
    from application.models.servers import publishHealth
    publishHealth(server)
    failed = any(outcome['status'] == FAILED for outcome in outcomes)
    # Named pairs: redaction then judges each value by its setting's name (`password_policy_length` is not a secret)
    before = [{'key': outcome['key'] or outcome['type'], 'value': redactValue(outcome['key'], outcome.get('before'))}
              for outcome in outcomes]
    return UnitResult(not failed, summary=unitSummary(outcomes), response={'rules': outcomes}, before=before)
