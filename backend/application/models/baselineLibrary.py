"""Baselines kept outside fleets: a user's saved baselines (named sets of rules in the database) and the presets
shipped with MFC (read-only JSON files). Either is copied into a fleet's baseline, never linked to it"""
import json
import os
import re
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from application.DBModels import Baseline, BaselineRule, Fleet, Server, db
from application.models.baselines import (RULE_TYPES, BaselineError, FleetSettings, addToBaseline, copyRules,
                                          ownedFleet, previewCopy, rulePayload, serializeRule, settingsOf,
                                          validateRules)

MAX_NAME_LENGTH = 120
MAX_DESCRIPTION_LENGTH = 500
MAX_SAVED = 200
PRESETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'baseline_presets')
PRESET_ID = re.compile(r'^[a-z0-9][a-z0-9-]{0,63}$')
# Types a preset cannot hold: a custom galaxy is copied from one of the user's servers
PRESET_EXCLUDED_TYPES = ('custom_galaxy',)
SOURCE_FIELDS = ('from_fleet_id', 'from_saved_id', 'from_preset')


# Presets

@lru_cache(maxsize=1)
def presets() -> Dict[str, dict]:
    """Every preset by ID (its file name), in name order. A file that cannot be read is an error: presets ship with
    the code and a test checks them"""
    found = {}
    for fileName in sorted(os.listdir(PRESETS_DIR)):
        presetId, extension = os.path.splitext(fileName)
        if extension != '.json' or not PRESET_ID.match(presetId):
            continue
        with open(os.path.join(PRESETS_DIR, fileName), encoding='utf-8') as file:
            data = json.load(file)
        found[presetId] = {
            'id': presetId,
            'name': data['name'],
            'description': data.get('description', ''),
            'rules': data['rules'],
        }
    return dict(sorted(found.items(), key=lambda item: item[1]['name'].lower()))


def preset(presetId: Any) -> dict:
    if not isinstance(presetId, str) or presetId not in presets():
        raise BaselineError('Unknown preset', 404)
    return presets()[presetId]


def checkPreset(data: dict) -> List[dict]:
    """A preset's rules, valid without any fleet. Used by the tests: a preset that does not pass is not shipped"""
    rules = data.get('rules')
    for index, rule in enumerate(rules or []):
        if rule.get('type') in PRESET_EXCLUDED_TYPES:
            raise BaselineError(f'Rule #{index + 1}: a preset cannot hold `{rule["type"]}` rules')
        if rule.get('force'):
            raise BaselineError(f'Rule #{index + 1}: a preset cannot force a server-specific setting')
    return validateRules(rules, FleetSettings())


# Serialization

def typeCounts(types: List[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for type in types:
        counts[type] = counts.get(type, 0) + 1
    return counts


def serializeSaved(baseline: Baseline, withRules: bool = False) -> dict:
    data = {
        'kind': 'saved',
        'id': baseline.id,
        'name': baseline.name,
        'description': baseline.description,
        'rule_count': len(baseline.rules),
        'types': typeCounts([rule.type for rule in baseline.rules]),
        'created': baseline.created,
        'updated': baseline.updated,
    }
    if withRules:
        data['rules'] = [serializeRule(rule) for rule in baseline.rules]
    return data


def serializePreset(data: dict, withRules: bool = False) -> dict:
    serialized = {
        'kind': 'preset',
        'id': data['id'],
        'name': data['name'],
        'description': data['description'],
        'rule_count': len(data['rules']),
        'types': typeCounts([rule['type'] for rule in data['rules']]),
    }
    if withRules:
        serialized['rules'] = [presetRule(rule) for rule in data['rules']]
    return serialized


def presetRule(rule: dict) -> dict:
    """A preset's rule shaped as a stored one, as given in its file"""
    return {
        'id': None,
        'type': rule['type'],
        'key': rule.get('key', ''),
        'label': rule.get('label', ''),
        'expected': rule.get('expected'),
        'comparator': rule.get('comparator', 'eq'),
        'severity': rule.get('severity', 'warning'),
        'note': rule.get('note', ''),
        'forced': False,
        'remediable': RULE_TYPES[rule['type']]['remediable'] if rule['type'] in RULE_TYPES else False,
    }


# Saved baselines

def savedQuery(user):
    return Baseline.query.filter(Baseline.fleet_id.is_(None), Baseline.user_id == user.id)


def ownedSaved(user, savedId: Any) -> Baseline:
    if isinstance(savedId, bool) or not isinstance(savedId, int):
        raise BaselineError('Unknown saved baseline', 404)
    baseline = savedQuery(user).filter(Baseline.id == savedId).first()
    if baseline is None:
        raise BaselineError('Unknown saved baseline', 404)
    return baseline


def serializeFleetSource(fleet: Fleet) -> dict:
    rules = fleet.baseline.rules if fleet.baseline else []
    return {
        'kind': 'fleet',
        'id': fleet.id,
        'name': fleet.name,
        'rule_count': len(rules),
        'types': typeCounts([rule.type for rule in rules]),
    }


def libraryForUser(user) -> dict:
    """The user's saved baselines, the presets, and the user's fleets with the size of their baselines (a fleet is
    a source too, and a target)"""
    saved = savedQuery(user).all()
    fleets = Fleet.query.filter_by(user_id=user.id).all()
    fleetNames = {fleet.id: fleet.name for fleet in fleets}
    servers = Server.query.filter_by(user_id=user.id).all()
    return {
        'saved': sorted([serializeSaved(baseline) for baseline in saved], key=lambda item: item['name'].lower()),
        'presets': [serializePreset(data) for data in presets().values()],
        'fleets': sorted([serializeFleetSource(fleet) for fleet in fleets], key=lambda item: item['name'].lower()),
        # Servers a new saved baseline can be picked from
        'servers': sorted([{'id': server.id, 'name': server.name, 'fleet_id': server.fleet_id,
                            'fleet_name': fleetNames.get(server.fleet_id, '')} for server in servers],
                          key=lambda item: (item['name'].lower(), item['id'])),
    }


def savedForUser(user, savedId: int) -> dict:
    return serializeSaved(ownedSaved(user, savedId), withRules=True)


def presetForUser(user, presetId: str) -> dict:
    return serializePreset(preset(presetId), withRules=True)


def checkedName(user, name: Any, exceptId: Optional[int] = None) -> str:
    if not isinstance(name, str) or name.strip() == '':
        raise BaselineError('A saved baseline needs a name', field='name')
    name = ' '.join(name.split())
    if len(name) > MAX_NAME_LENGTH:
        raise BaselineError(f'A name has at most {MAX_NAME_LENGTH} characters', field='name')
    taken = savedQuery(user).filter(db.func.lower(Baseline.name) == name.lower())
    if exceptId is not None:
        taken = taken.filter(Baseline.id != exceptId)
    other = taken.first()
    if other is not None:
        raise BaselineError(f'You already have a saved baseline named “{other.name}”', 409, field='name',
                            code='name_taken')
    return name


def checkedDescription(description: Any) -> str:
    if description is None:
        return ''
    if not isinstance(description, str):
        raise BaselineError('`description` must be a text', field='description')
    description = description.strip()
    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise BaselineError(f'A description has at most {MAX_DESCRIPTION_LENGTH} characters', field='description')
    return description


def fleetRules(user, fleetId: Any, field: str = 'from_fleet_id') -> Tuple[Any, List[dict]]:
    """The fleet and its rules, as stored (they were valid when added)"""
    if isinstance(fleetId, bool) or not isinstance(fleetId, int):
        raise BaselineError(f'`{field}` must be a fleet ID', field=field)
    fleet = ownedFleet(user, fleetId)
    if fleet.baseline is None or len(fleet.baseline.rules) == 0:
        raise BaselineError(f'Fleet `{fleet.name}` has no baseline rules', field=field, code='empty_source')
    return fleet, [rulePayload(rule) for rule in fleet.baseline.rules]


def referenceSettings(user, serverId: Any) -> FleetSettings:
    """Rules taken from a reference server are checked with that server's setting types"""
    if serverId is None:
        return FleetSettings(owner_id=user.id)
    if isinstance(serverId, bool) or not isinstance(serverId, int):
        raise BaselineError('`server_id` must be a server ID', field='server_id')
    server = Server.query.filter_by(id=serverId, user_id=user.id).first()
    if server is None:
        raise BaselineError('Unknown server', 404, field='server_id')
    return FleetSettings(owner_id=user.id, servers=[server])


def storedRules(validRules: List[dict], now: int) -> List[BaselineRule]:
    return [BaselineRule(**rule, created=now, updated=now) for rule in validRules]


def copiedRules(rules: List[BaselineRule], now: int) -> List[BaselineRule]:
    """Copies of a fleet's rules: they keep what they expect, forced included"""
    return [BaselineRule(type=rule.type, key=rule.key, label=rule.label, expected=rule.expected,
                         comparator=rule.comparator, severity=rule.severity, note=rule.note, forced=rule.forced,
                         created=now, updated=now) for rule in rules]


def createSaved(user, body: dict) -> dict:
    """`{name, description?, from_fleet_id}` keeps a copy of a fleet's rules; `{name, description?, rules,
    server_id?}` keeps rules picked on a reference server (validated with its setting types); `{name,
    description?}` alone starts an empty one, to fill rule by rule"""
    if savedQuery(user).count() >= MAX_SAVED:
        raise BaselineError(f'You can keep at most {MAX_SAVED} saved baselines')
    name = checkedName(user, body.get('name'))
    description = checkedDescription(body.get('description'))
    now = int(time.time())
    if body.get('from_fleet_id') is not None:
        fleet, _ = fleetRules(user, body.get('from_fleet_id'))
        rules = copiedRules(fleet.baseline.rules, now)
    elif 'rules' in body:
        rules = storedRules(validateRules(body.get('rules'), referenceSettings(user, body.get('server_id'))), now)
    else:
        rules = []
    baseline = Baseline(user_id=user.id, name=name, description=description, created=now, updated=now)
    baseline.rules = rules
    db.session.add(baseline)
    db.session.commit()
    return serializeSaved(baseline, withRules=True)


def updateSaved(user, savedId: int, body: dict) -> dict:
    """`{name?, description?, from_fleet_id?}`: renames, describes, or takes a fleet's rules again (all of them,
    in place of its own)"""
    baseline = ownedSaved(user, savedId)
    if 'name' in body:
        baseline.name = checkedName(user, body['name'], exceptId=baseline.id)
    if 'description' in body:
        baseline.description = checkedDescription(body['description'])
    now = int(time.time())
    if body.get('from_fleet_id') is not None:
        fleet, _ = fleetRules(user, body['from_fleet_id'])
        baseline.rules = []
        db.session.flush()
        baseline.rules = copiedRules(fleet.baseline.rules, now)
    baseline.updated = now
    db.session.commit()
    return serializeSaved(baseline, withRules=True)


def addSavedRules(user, savedId: int, rules: Any, onConflict: str = 'error') -> dict:
    """Adds rules to a saved baseline, as to a fleet's: all or none, `on_conflict` for rules already in it"""
    baseline = ownedSaved(user, savedId)
    valid = validateRules(rules, settingsOf(baseline))
    addToBaseline(baseline, valid, onConflict, int(time.time()))
    db.session.commit()
    return serializeSaved(baseline, withRules=True)


def deleteSaved(user, savedId: int) -> None:
    db.session.delete(ownedSaved(user, savedId))
    db.session.commit()


# Copying into a fleet

def copySource(user, fleetId: int, body: dict) -> Tuple[dict, List[dict]]:
    """The source named by exactly one of `from_fleet_id`, `from_saved_id`, `from_preset`, and its rules"""
    given = [field for field in SOURCE_FIELDS if body.get(field) is not None]
    if len(given) != 1:
        raise BaselineError('Name one source: `from_fleet_id`, `from_saved_id` or `from_preset`',
                            field='from_fleet_id')
    field = given[0]
    if field == 'from_fleet_id':
        if body[field] == fleetId:
            raise BaselineError('A fleet cannot copy its own baseline', field=field)
        fleet, payloads = fleetRules(user, body[field])
        return {'kind': 'fleet', 'id': fleet.id, 'name': fleet.name}, payloads
    if field == 'from_saved_id':
        baseline = ownedSaved(user, body[field])
        if len(baseline.rules) == 0:
            raise BaselineError(f'`{baseline.name}` has no rules yet', field=field, code='empty_source')
        return {'kind': 'saved', 'id': baseline.id, 'name': baseline.name}, \
            [rulePayload(rule) for rule in baseline.rules]
    data = preset(body[field])
    return {'kind': 'preset', 'id': data['id'], 'name': data['name']}, [dict(rule) for rule in data['rules']]


def copyMode(body: dict) -> str:
    return body.get('mode') or 'replace'


def previewCopyForUser(user, fleetId: int, body: dict) -> dict:
    ownedFleet(user, fleetId)
    source, payloads = copySource(user, fleetId, body)
    return {'source': source, **previewCopy(user, fleetId, payloads, copyMode(body))}


def copyForUser(user, fleetId: int, body: dict) -> dict:
    ownedFleet(user, fleetId)
    _, payloads = copySource(user, fleetId, body)
    return copyRules(user, fleetId, payloads, copyMode(body))
