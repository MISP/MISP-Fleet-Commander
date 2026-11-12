#!/usr/bin/env python3
"""Fixing baseline drift. A preview lists what a fix would change (`server · rule · current → expected`) and what
must be done by hand; confirming starts a `baseline_remediation` job, one unit per server applying that server's
drifting rules in order. Each unit reads every value back from MISP, updates the server's snapshot with what it
read and publishes the server's health, so the drift matrix and the issues follow without a refresh"""

import time
from typing import Any, Dict, List, Optional

from application import redisModel
from application.DBModels import Server
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

def manualReason(baselineRule: dict, result, entries: Dict[str, dict]) -> Optional[str]:
    """Why a drifting rule cannot be fixed from here, or None"""
    if baselineRule['type'] == 'version_min':
        return 'Upgrade MISP on this server'
    if baselineRule['type'] == 'setting':
        entry = entries.get(baselineRule['key']) or {}
        if entry.get('cli_only') or entry.get('editable') is False:
            return 'MISP only lets this setting change from its command line'
        return None
    if result.actual is None:
        return 'Not on this server: update its taxonomies, galaxies or object templates in MISP first'
    return None


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
            reason = manualReason(rule, result, entries)
            action = MANUAL if reason else APPLY
            counts[action] += 1
            items.append({
                'rule_id': rule['id'],
                'type': rule['type'],
                'key': rule['key'],
                'label': rule['label'],
                'severity': rule['severity'],
                'comparator': rule['comparator'],
                'expected': rule['expected'],
                'current': result.actual,
                'action': action,
                'reason': reason or '',
            })
        if items:
            servers.append({'id': server.id, 'name': server.name, 'items': items})
    counts['servers'] = sum(1 for server in servers if any(item['action'] == APPLY for item in server['items']))
    return {'fleet_id': fleet.id, 'servers': servers, 'excluded': excluded, 'counts': counts}


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

class ContentCache:
    """Each content index is listed once before the writes and once after, to check them"""

    def __init__(self, server):
        self.server = server
        self.parsed = {}

    def get(self, type: str) -> Dict[str, dict]:
        if type not in self.parsed:
            from application.models.baselineDrift import CONTENT_INDEXES
            (url, model, what), _ = CONTENT_INDEXES[type]
            records = mispOps.listing(self.server, url, model, what)
            self.parsed[type] = parsedContent(type, records)
        return self.parsed[type]


def parsedContent(type: str, records: list) -> Dict[str, dict]:
    """key → {id, enabled} for any content type"""
    if type == 'taxonomy_enabled':
        return mispOps.parseTaxonomies(records)
    if type == 'galaxy_enabled':
        return mispOps.parseGalaxies(records)
    return {uuid: {**template, 'enabled': template['active']}
            for uuid, template in mispOps.parseObjectTemplates(records).items()}


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


def applyItems(server, items: List[dict]) -> List[dict]:
    """Applies each rule in order, then checks the content ones against a fresh listing"""
    cache = ContentCache(server)
    outcomes = []
    for item in items:
        outcome = {'rule_id': item.get('rule_id'), 'type': item.get('type'), 'key': item.get('key'),
                   'label': item.get('label') or '', 'expected': item.get('expected')}
        try:
            if item.get('type') == 'setting':
                outcome.update(applySetting(server, item))
            elif item.get('type') in drift.CONTENT_SECTIONS:
                outcome.update(applyContent(server, item, cache))
            else:
                outcome.update(status=FAILED, message='This rule cannot be fixed from here')
        except mispOps.MispOpError as e:
            outcome.update(status=FAILED, message=e.message)
        except Exception as e:
            outcome.update(status=FAILED, message=f'Unexpected error: {e}')
        outcomes.append(outcome)

    touched = {o['type'] for o in outcomes if o['type'] in drift.CONTENT_SECTIONS and o['status'] == FIXED}
    fresh = ContentCache(server)
    for outcome in outcomes:
        if outcome['type'] not in touched or outcome['status'] != FIXED:
            continue
        try:
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
        for type, parsed in fresh.parsed.items():
            section = drift.CONTENT_SECTIONS[type]
            known = state.get(section, {}).get('items') if isinstance(state.get(section), dict) else None
            known = known if isinstance(known, dict) else {}
            # Names come from the last listing; states from this one
            state[section] = {'items': {key: {**known.get(key, {}), 'enabled': value['enabled']}
                                        for key, value in parsed.items()}}
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
    outcomes, fresh = applyItems(server, items)
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
