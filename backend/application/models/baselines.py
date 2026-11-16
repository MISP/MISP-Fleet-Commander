#!/usr/bin/env python3
"""Baselines: the configuration a fleet's servers are expected to have, as a list of rules. A rule names what is
checked (`type` and `key`) and the value expected; this module validates and stores rules. Drift is evaluated from
the servers' snapshots, and fixed through jobs.

Organisations, sharing groups and custom galaxies are expected as objects describing the item (its name, members,
clusters, …), as a reference server lists them, so that a fix can create the item where it is missing.

Settings that are specific to each server (its URL, its organisation, its GnuPG key, …) are refused unless the rule
is explicitly forced. Secrets are refused outright: a baseline is stored in clear, and MISP hides their value anyway"""

import json
import math
import re
import time
from typing import Any, Dict, List, Optional

from application import redisModel
from application.DBModels import (BASELINE_COMPARATORS, BASELINE_RULE_TYPES, BASELINE_SEVERITIES, Baseline,
                                  BaselineRule, Fleet, Server, db)
from application.health.versions import format_version, parse_version
from application.models.jobs import isSensitiveSetting
from application.models.mispOps import snapshotSettings

MAX_RULES = 2000
MAX_KEY_LENGTH = 255
MAX_LABEL_LENGTH = 255
MAX_NOTE_LENGTH = 500
MAX_EXPECTED_BYTES = 8 * 1024
CONFLICT_MODES = ('error', 'skip', 'replace')
COPY_MODES = ('replace', 'merge')

# Settings that identify a server or hold its own keys: copying them across a fleet would break the servers
SERVER_SPECIFIC_SETTINGS = (
    'MISP.baseurl', 'MISP.external_baseurl', 'MISP.uuid', 'MISP.org', 'MISP.host_org_id', 'MISP.email',
    'MISP.main_logo', 'Security.salt', 'Security.encryption_key',
)
SERVER_SPECIFIC_PREFIXES = ('GnuPG.', 'SMIME.')

SETTING_NAME = re.compile(r'^[A-Za-z0-9_-]+(\.[A-Za-z0-9_-]+)+$')
NAMESPACE = re.compile(r'^[^\s]+$')
UUID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
TRUE_WORDS = ('1', 'true', 'yes', 'on', 'enabled')
FALSE_WORDS = ('0', 'false', 'no', 'off', 'disabled', '')

# What each type checks. `key`: what names the item; `expected`: the kind of value; `comparators`: allowed ones,
# the first being the default
RULE_TYPES = {
    'setting': {
        'label': 'MISP setting',
        'key': 'setting',
        'expected': 'setting value',
        'comparators': ('eq', 'gte', 'lte'),
        'remediable': True,
    },
    'taxonomy_enabled': {
        'label': 'Taxonomy enabled',
        'key': 'namespace',
        'expected': 'boolean',
        'comparators': ('eq',),
        'remediable': True,
    },
    'galaxy_enabled': {
        'label': 'Galaxy enabled',
        'key': 'uuid',
        'expected': 'boolean',
        'comparators': ('eq',),
        'remediable': True,
    },
    'object_template_active': {
        'label': 'Object template active',
        'key': 'uuid',
        'expected': 'boolean',
        'comparators': ('eq',),
        'remediable': True,
    },
    'version_min': {
        'label': 'Minimum MISP version',
        'key': None,
        'expected': 'version',
        'comparators': ('gte',),
        'remediable': False,
    },
    # Present, with the given name and, when the rule sets them, type, nationality, sector and local/external
    'organisation': {
        'label': 'Organisation',
        'key': 'uuid',
        'expected': 'organisation',
        'comparators': ('eq',),
        'remediable': True,
    },
    # Present, with the given name (releasability and description when set) and at least the given members
    'sharing_group': {
        'label': 'Sharing group',
        'key': 'uuid',
        'expected': 'sharing group',
        'comparators': ('eq',),
        'remediable': True,
    },
    # Present, enabled, with the given clusters at the given version or newer. Fixed from `source_server_id`
    'custom_galaxy': {
        'label': 'Custom galaxy',
        'key': 'uuid',
        'expected': 'custom galaxy',
        'comparators': ('eq',),
        'remediable': True,
    },
}
assert tuple(RULE_TYPES) == BASELINE_RULE_TYPES

# Rule types whose expected value is an object describing the item, taken from a reference server
STRUCTURED_TYPES = ('organisation', 'sharing_group', 'custom_galaxy')
MAX_MEMBERS = 2000
MAX_CLUSTERS = 20000
# A sharing group's members and a galaxy's clusters take more room than a setting value
MAX_EXPECTED_BYTES_BY_TYPE = {'sharing_group': 256 * 1024, 'custom_galaxy': 1024 * 1024}


class BaselineError(Exception):
    def __init__(self, message: str, status: int = 400, field: Optional[str] = None, code: Optional[str] = None,
                 errors: Optional[List[dict]] = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.field = field
        # `server_specific` tells the client that `force` would accept the rule
        self.code = code
        # Per-rule errors of a list of rules: [{index, message, field, code}]
        self.errors = errors

    def toDict(self) -> dict:
        data = {'message': self.message}
        for name in ('field', 'code', 'errors'):
            if getattr(self, name) is not None:
                data[name] = getattr(self, name)
        return data


def isServerSpecificSetting(name: str) -> bool:
    return name in SERVER_SPECIFIC_SETTINGS or name.startswith(SERVER_SPECIFIC_PREFIXES)


def ruleTypes() -> dict:
    """What the rule editor needs to know"""
    return {
        'types': [{'type': type, **{k: list(v) if isinstance(v, tuple) else v for k, v in meta.items()}}
                  for type, meta in RULE_TYPES.items()],
        'severities': list(BASELINE_SEVERITIES),
        'server_specific_settings': list(SERVER_SPECIFIC_SETTINGS),
        'server_specific_prefixes': list(SERVER_SPECIFIC_PREFIXES),
        'max_rules': MAX_RULES,
    }


# Validation

class FleetSettings:
    """The settings the fleet's servers report in their snapshots, read once per request: their types and whether
    MISP redacts them"""

    def __init__(self, fleet: Optional[Fleet] = None, owner_id: Optional[int] = None,
                 servers: Optional[List[Server]] = None):
        """For a saved baseline, there is no fleet: the rules' owner, and the servers whose settings give the types
        (none: values are kept as given until the rules are copied into a fleet)"""
        self.fleet = fleet
        self.owner_id = fleet.user_id if fleet is not None else owner_id
        self._servers = servers
        self._entries = None

    def servers(self) -> List[Server]:
        if self._servers is None:
            self._servers = Server.query.filter_by(fleet_id=self.fleet.id).all() if self.fleet is not None else []
        return self._servers

    def entries(self) -> Dict[str, List[dict]]:
        if self._entries is None:
            self._entries = {}
            for server in self.servers():
                for name, entry in snapshotSettings(redisModel.getServerInfo(server.uuid)).items():
                    self._entries.setdefault(name, []).append(entry)
        return self._entries

    def isRedacted(self, name: str) -> bool:
        return any(entry.get('redacted') for entry in self.entries().get(name, []))

    def type(self, name: str) -> Optional[str]:
        for entry in self.entries().get(name, []):
            if entry.get('type') in ('boolean', 'numeric', 'float', 'string'):
                return entry['type']
        return None

    def checkSourceServer(self, server_id: int) -> None:
        """A server content is copied from must be the rules' owner's. One deleted since is accepted: the rule's fix
        then has to be done by hand"""
        server = db.session.get(Server, server_id)
        if server is not None and server.user_id != self.owner_id:
            raise BaselineError('Unknown source server', field='expected')


def asBoolean(value: Any, field: str = 'expected') -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str) and value.strip().lower() in TRUE_WORDS + FALSE_WORDS:
        return value.strip().lower() in TRUE_WORDS
    raise BaselineError('Expected `true` or `false`', field=field)


def asNumber(value: Any, integer: bool, field: str = 'expected'):
    if isinstance(value, bool):
        raise BaselineError('Expected a number', field=field)
    if isinstance(value, str):
        try:
            value = float(value.strip())
        except ValueError:
            raise BaselineError('Expected a number', field=field)
    if not isinstance(value, (int, float)) or math.isnan(value) or math.isinf(value):
        raise BaselineError('Expected a number', field=field)
    if integer:
        if value != int(value):
            raise BaselineError('Expected a whole number', field=field)
        return int(value)
    return int(value) if isinstance(value, int) or value == int(value) else float(value)


def checkSettingKey(name: str, force: bool, settings: FleetSettings) -> bool:
    """Whether the rule is forced: True for an accepted server-specific setting"""
    if not SETTING_NAME.match(name):
        raise BaselineError('A setting name looks like `MISP.live` or `Security.password_policy_length`', field='key')
    if isSensitiveSetting(name) or settings.isRedacted(name):
        raise BaselineError(f'`{name}` holds a secret: baselines do not manage secrets', field='key', code='secret')
    if isServerSpecificSetting(name):
        if not force:
            raise BaselineError(f'`{name}` is usually different on each server. Force the rule to keep it anyway',
                                field='key', code='server_specific')
        return True
    return False


def settingExpected(name: str, expected: Any, comparator: str, settings: FleetSettings) -> Any:
    """The expected value in the setting's type, when a server of the fleet reports that type"""
    settingType = settings.type(name)
    if comparator in ('gte', 'lte'):
        if settingType not in (None, 'numeric', 'float'):
            raise BaselineError(f'`{name}` is not a number: it can only be compared with `eq`', field='comparator')
        return asNumber(expected, integer=settingType == 'numeric')
    if settingType == 'boolean':
        return asBoolean(expected)
    if settingType in ('numeric', 'float') and expected not in (None, ''):
        return asNumber(expected, integer=settingType == 'numeric')
    if settingType == 'string' and expected is not None and not isinstance(expected, str):
        if isinstance(expected, bool) or not isinstance(expected, (int, float)):
            raise BaselineError('Expected a text value', field='expected')
        return str(expected)
    if expected is not None and not isinstance(expected, (bool, int, float, str)):
        raise BaselineError('Expected a single value (text, number or boolean)', field='expected')
    return expected


def galaxyLabel(namespace: Optional[str], name: str) -> str:
    return f'{namespace} :: {name}' if namespace else name


def knownLabel(type: str, key: str) -> str:
    """The name of a galaxy or object template MISP ships, from the plugins' lists"""
    if type == 'galaxy_enabled':
        from application.plugins.ToggleGalaxy import ALL_GALAXIES
        for galaxy in ALL_GALAXIES:
            if str(galaxy.get('uuid', '')).lower() == key:
                return galaxyLabel(galaxy.get('namespace'), galaxy['name'])
    if type == 'object_template_active':
        from application.plugins.ToggleObject import ALL_TEMPLATES
        for template in ALL_TEMPLATES:
            if str(template.get('uuid', '')).lower() == key:
                return template['name']
    return ''


def text(payload: dict, field: str, maxLength: int, name: Optional[str] = None) -> str:
    """`name`: the field to blame, when it is not `field` itself (a part of `expected`)"""
    value = payload.get(field)
    if value is None:
        return ''
    if not isinstance(value, str):
        raise BaselineError(f'`{field}` must be a text', field=name or field)
    value = value.strip()
    if len(value) > maxLength:
        raise BaselineError(f'`{field}` is longer than {maxLength} characters', field=name or field)
    return value


def uuidOf(value: Any, what: str, field: str = 'expected') -> str:
    key = value.strip().lower() if isinstance(value, str) else ''
    if not UUID.match(key):
        raise BaselineError(f'{what} must be a UUID', field=field)
    return key


def expectedObject(expected: Any) -> dict:
    if not isinstance(expected, dict):
        raise BaselineError('Expected an object describing the item, as a reference server lists it', field='expected')
    return expected


def requiredName(expected: dict) -> str:
    name = text(expected, 'name', MAX_LABEL_LENGTH, 'expected')
    if name == '':
        raise BaselineError('`expected.name` is required', field='expected')
    return name


def optionalBoolean(expected: dict, field: str) -> Optional[bool]:
    value = expected.get(field)
    return None if value is None else asBoolean(value)


def organisationExpected(expected: Any) -> dict:
    """Name always; type, nationality and sector when not empty; `local` when true or false. What is left out is not
    checked"""
    expected = expectedObject(expected)
    normalised = {'name': requiredName(expected)}
    for field in ('type', 'nationality', 'sector'):
        value = text(expected, field, MAX_LABEL_LENGTH, 'expected')
        if value:
            normalised[field] = value
    local = optionalBoolean(expected, 'local')
    if local is not None:
        normalised['local'] = local
    return normalised


def sharingGroupExpected(expected: Any) -> dict:
    """Name, releasability, description, whether it is active (when set), roaming (used when it is created) and the
    members it must have at least, by organisation UUID (their names create the missing ones)"""
    expected = expectedObject(expected)
    members = expected.get('members', [])
    if not isinstance(members, list):
        raise BaselineError('`expected.members` must be a list of organisations', field='expected')
    if len(members) > MAX_MEMBERS:
        raise BaselineError(f'A sharing group rule has at most {MAX_MEMBERS} members', field='expected')
    byUuid = {}
    for member in members:
        if not isinstance(member, dict):
            raise BaselineError('Each member is an organisation: `{uuid, name}`', field='expected')
        uuid = uuidOf(member.get('uuid'), 'A member’s `uuid`')
        byUuid[uuid] = {'uuid': uuid, 'name': requiredName(member),
                        'extend': optionalBoolean(member, 'extend') is True}
    normalised = {
        'name': requiredName(expected),
        'releasability': text(expected, 'releasability', 4096, 'expected'),
        'description': text(expected, 'description', 4096, 'expected'),
        'roaming': optionalBoolean(expected, 'roaming') is True,
        'members': sorted(byUuid.values(), key=lambda member: (member['name'].lower(), member['uuid'])),
    }
    active = optionalBoolean(expected, 'active')
    if active is not None:
        normalised['active'] = active
    return normalised


def customGalaxyExpected(expected: Any, settings: 'FleetSettings') -> dict:
    """Its name, its clusters (UUID → the version a server must have at least) and the server it is copied from"""
    expected = expectedObject(expected)
    clusters = expected.get('clusters', {})
    if not isinstance(clusters, dict):
        raise BaselineError('`expected.clusters` must map cluster UUIDs to versions', field='expected')
    if len(clusters) > MAX_CLUSTERS:
        raise BaselineError(f'A custom galaxy rule has at most {MAX_CLUSTERS} clusters', field='expected')
    normalisedClusters = {}
    for uuid, version in clusters.items():
        normalisedClusters[uuidOf(uuid, 'A cluster’s UUID')] = asNumber(version, integer=True)
    source = expected.get('source_server_id')
    if isinstance(source, bool) or not isinstance(source, int):
        raise BaselineError('`expected.source_server_id` must be the ID of the server the galaxy is copied from',
                            field='expected')
    settings.checkSourceServer(source)
    return {
        'name': requiredName(expected),
        'namespace': text(expected, 'namespace', MAX_LABEL_LENGTH, 'expected'),
        'source_server_id': source,
        'clusters': dict(sorted(normalisedClusters.items())),
    }


def structuredLabel(type: str, expected: dict) -> str:
    if type == 'custom_galaxy':
        return galaxyLabel(expected.get('namespace'), expected['name'])
    return expected['name']


def validateRule(payload: Any, settings: FleetSettings) -> dict:
    """The rule's columns from a client's rule, normalised. Raises BaselineError naming the faulty field"""
    if not isinstance(payload, dict):
        raise BaselineError('A rule must be an object')
    type = payload.get('type')
    if type not in RULE_TYPES:
        raise BaselineError(f"`type` must be one of {', '.join(RULE_TYPES)}", field='type')
    meta = RULE_TYPES[type]

    comparator = payload.get('comparator') or meta['comparators'][0]
    if comparator not in meta['comparators']:
        raise BaselineError(f"`comparator` must be {' or '.join(meta['comparators'])} for this type", field='comparator')
    severity = payload.get('severity') or 'warning'
    if severity not in BASELINE_SEVERITIES:
        raise BaselineError(f"`severity` must be one of {', '.join(BASELINE_SEVERITIES)}", field='severity')
    force = payload.get('force', payload.get('forced')) is True
    forced = False

    key = payload.get('key')
    if meta['key'] is None:
        key = ''
    elif not isinstance(key, str) or key.strip() == '':
        raise BaselineError('`key` is required', field='key')
    else:
        key = key.strip()
        if len(key) > MAX_KEY_LENGTH:
            raise BaselineError(f'`key` is longer than {MAX_KEY_LENGTH} characters', field='key')

    expected = payload.get('expected')
    label = text(payload, 'label', MAX_LABEL_LENGTH)
    if type == 'setting':
        forced = checkSettingKey(key, force, settings)
        expected = settingExpected(key, expected, comparator, settings)
    elif type == 'version_min':
        version = parse_version(expected if isinstance(expected, str) else None)
        if version is None:
            raise BaselineError('Expected a MISP version such as `2.5.20`', field='expected')
        expected = format_version(version)
    elif type in STRUCTURED_TYPES:
        key = uuidOf(key, '`key`', field='key')
        if type == 'organisation':
            expected = organisationExpected(expected)
        elif type == 'sharing_group':
            expected = sharingGroupExpected(expected)
        else:
            expected = customGalaxyExpected(expected, settings)
        # Named after the item, whatever the client sent: the name is part of what is checked
        label = structuredLabel(type, expected)[:MAX_LABEL_LENGTH]
    else:
        if meta['key'] == 'uuid':
            key = key.lower()
            if not UUID.match(key):
                raise BaselineError('`key` must be the UUID of the item', field='key')
        elif not NAMESPACE.match(key):
            raise BaselineError('`key` must be a taxonomy namespace, such as `tlp`', field='key')
        expected = asBoolean(True if expected is None else expected)

    maxBytes = MAX_EXPECTED_BYTES_BY_TYPE.get(type, MAX_EXPECTED_BYTES)
    if len(json.dumps(expected)) > maxBytes:
        raise BaselineError(f'`expected` is larger than {maxBytes // 1024} KB', field='expected')

    return {
        'type': type,
        'key': key,
        'label': label or knownLabel(type, key),
        'expected': expected,
        'comparator': comparator,
        'severity': severity,
        'note': text(payload, 'note', MAX_NOTE_LENGTH),
        'forced': forced,
    }


# Serialization

def serializeRule(rule: BaselineRule) -> dict:
    return {
        'id': rule.id,
        'type': rule.type,
        'key': rule.key,
        'label': rule.label,
        'expected': rule.expected,
        'comparator': rule.comparator,
        'severity': rule.severity,
        'note': rule.note,
        'forced': rule.forced,
        'remediable': RULE_TYPES[rule.type]['remediable'] if rule.type in RULE_TYPES else False,
        'created': rule.created,
        'updated': rule.updated,
    }


def serializedRulesOfFleet(fleet_id: int) -> List[dict]:
    rules = BaselineRule.query.join(Baseline).filter(Baseline.fleet_id == fleet_id).order_by(BaselineRule.id).all()
    return [serializeRule(rule) for rule in rules]


def serializeBaseline(fleet: Fleet) -> dict:
    baseline = fleet.baseline
    return {
        'id': baseline.id if baseline else None,
        'fleet_id': fleet.id,
        'created': baseline.created if baseline else None,
        'updated': baseline.updated if baseline else None,
        'rules': [serializeRule(rule) for rule in baseline.rules] if baseline else [],
    }


# Operations

def ownedFleet(user, fleet_id: int) -> Fleet:
    fleet = Fleet.query.filter_by(id=fleet_id, user_id=user.id).first()
    if fleet is None:
        raise BaselineError('Unknown fleet', 404)
    return fleet


def ownedRule(user, rule_id: int) -> BaselineRule:
    rule = BaselineRule.query.join(Baseline).join(Fleet) \
        .filter(BaselineRule.id == rule_id, Fleet.user_id == user.id).first()
    if rule is None:
        raise BaselineError('Unknown rule', 404)
    return rule


def ensureBaseline(fleet: Fleet, now: int) -> Baseline:
    if fleet.baseline is None:
        fleet.baseline = Baseline(created=now, updated=now)
        db.session.add(fleet.baseline)
    return fleet.baseline


def getForUser(user, fleet_id: int) -> dict:
    return serializeBaseline(ownedFleet(user, fleet_id))


def validateRules(rules: Any, settings: FleetSettings) -> List[dict]:
    """All of them or none: the errors of every invalid rule, with its index"""
    if not isinstance(rules, list) or len(rules) == 0:
        raise BaselineError('`rules` must be a non-empty list of rules', field='rules')
    if len(rules) > MAX_RULES:
        raise BaselineError(f'A baseline has at most {MAX_RULES} rules', field='rules')
    valid, errors, seen = [], [], {}
    for index, payload in enumerate(rules):
        try:
            rule = validateRule(payload, settings)
        except BaselineError as e:
            errors.append({'index': index, 'message': e.message, 'field': e.field, 'code': e.code})
            continue
        identity = (rule['type'], rule['key'])
        if identity in seen:
            errors.append({'index': index, 'message': f'Same rule as #{seen[identity] + 1}', 'field': 'key',
                           'code': 'duplicate'})
            continue
        seen[identity] = index
        valid.append(rule)
    if errors:
        raise BaselineError(f"{len(errors)} rule{'s are' if len(errors) > 1 else ' is'} invalid", errors=errors)
    return valid


def applyRules(fleet: Fleet, rules: List[dict], onConflict: str, now: int) -> None:
    baseline = ensureBaseline(fleet, now)
    existing = {(rule.type, rule.key): rule for rule in baseline.rules}
    conflicts = [rule for rule in rules if (rule['type'], rule['key']) in existing]
    if conflicts and onConflict == 'error':
        raise BaselineError(
            f"{len(conflicts)} rule{'s' if len(conflicts) > 1 else ''} already in the baseline", 409,
            errors=[{'index': rules.index(rule), 'message': 'Already in the baseline', 'field': 'key',
                     'code': 'exists', 'rule_id': existing[(rule['type'], rule['key'])].id} for rule in conflicts])
    added = [rule for rule in rules if (rule['type'], rule['key']) not in existing]
    if len(baseline.rules) + len(added) > MAX_RULES:
        raise BaselineError(f'A baseline has at most {MAX_RULES} rules', field='rules')
    for rule in rules:
        current = existing.get((rule['type'], rule['key']))
        if current is None:
            baseline.rules.append(BaselineRule(**rule, created=now, updated=now))
        elif onConflict == 'replace':
            for column, value in rule.items():
                setattr(current, column, value)
            current.updated = now
    baseline.updated = now


def addRules(user, fleet_id: int, rules: Any, onConflict: str = 'error') -> dict:
    """Adds rules to the fleet's baseline, creating it if needed. A rule already present (same type and key) is an
    error (409), is left as it is (`skip`) or is overwritten (`replace`)"""
    if onConflict not in CONFLICT_MODES:
        raise BaselineError(f"`on_conflict` must be one of {', '.join(CONFLICT_MODES)}", field='on_conflict')
    fleet = ownedFleet(user, fleet_id)
    valid = validateRules(rules, FleetSettings(fleet))
    applyRules(fleet, valid, onConflict, int(time.time()))
    db.session.commit()
    rulesChanged(fleet)
    return serializeBaseline(fleet)


def updateRule(user, rule_id: int, changes: Any) -> dict:
    """Changes what a rule expects. Its type and key cannot change: that is another rule"""
    if not isinstance(changes, dict):
        raise BaselineError('The body must be a JSON object')
    rule = ownedRule(user, rule_id)
    for field in ('type', 'key'):
        if field in changes and changes[field] != getattr(rule, field):
            raise BaselineError(f'`{field}` cannot be changed: add another rule instead', field=field)
    payload = {**serializeRule(rule), **changes, 'type': rule.type, 'key': rule.key,
               'force': changes.get('force', rule.forced)}
    valid = validateRule(payload, FleetSettings(rule.baseline.fleet))
    now = int(time.time())
    for column, value in valid.items():
        setattr(rule, column, value)
    rule.updated = now
    rule.baseline.updated = now
    db.session.commit()
    rulesChanged(rule.baseline.fleet)
    return serializeRule(rule)


def deleteRules(user, fleet_id: int, rule_ids: Any) -> dict:
    """Removes rules of the fleet's baseline: the given ones, or all of them when `rule_ids` is None"""
    fleet = ownedFleet(user, fleet_id)
    if fleet.baseline is None:
        if rule_ids is None:
            return serializeBaseline(fleet)
        raise BaselineError('Unknown rule', 404)
    if rule_ids is None:
        fleet.baseline = None
        db.session.commit()
        rulesChanged(fleet)
        return serializeBaseline(fleet)
    if not isinstance(rule_ids, list) or any(isinstance(id, bool) or not isinstance(id, int) for id in rule_ids):
        raise BaselineError('`rule_ids` must be a list of rule IDs', field='rule_ids')
    byId = {rule.id: rule for rule in fleet.baseline.rules}
    missing = [id for id in rule_ids if id not in byId]
    if missing:
        raise BaselineError(f"Unknown rule{'s' if len(missing) > 1 else ''}: {', '.join(map(str, missing))}", 404)
    for id in set(rule_ids):
        fleet.baseline.rules.remove(byId[id])
    fleet.baseline.updated = int(time.time())
    db.session.commit()
    rulesChanged(fleet)
    return serializeBaseline(fleet)


def deleteRule(user, rule_id: int) -> None:
    rule = ownedRule(user, rule_id)
    baseline = rule.baseline
    baseline.rules.remove(rule)
    baseline.updated = int(time.time())
    db.session.commit()
    rulesChanged(baseline.fleet)


# Copying rules into a fleet (from another fleet, a saved baseline or a preset)

# What makes two rules with the same type and key differ (the label only names the key)
COMPARED_COLUMNS = ('expected', 'comparator', 'severity', 'note', 'forced')


def rulePayload(rule: BaselineRule) -> dict:
    """A stored rule as `validateRule` takes it: a forced rule stays forced"""
    payload = serializeRule(rule)
    payload['force'] = rule.forced
    return payload


def plannedRule(rule: dict) -> dict:
    """A validated rule that is not stored yet, shaped as a serialized one"""
    return {**rule, 'id': None, 'remediable': RULE_TYPES[rule['type']]['remediable']}


class CopyPlan:
    """What copying `payloads` into the fleet's baseline changes. The rules are validated against this fleet: a
    server-specific setting stays allowed only because its rule was forced. `replace` makes the baseline identical
    to the source (rules kept as they are keep their ID, so their drift history), `merge` adds the source's rules and
    overwrites those with the same type and key"""

    def __init__(self, fleet: Fleet, payloads: List[dict], mode: str):
        if mode not in COPY_MODES:
            raise BaselineError(f"`mode` must be one of {', '.join(COPY_MODES)}", field='mode')
        self.fleet = fleet
        self.mode = mode
        self.rules = validateRules(payloads, FleetSettings(fleet))
        current = {(rule.type, rule.key): rule for rule in fleet.baseline.rules} if fleet.baseline else {}
        self.added, self.replaced, self.unchanged = [], [], 0
        for rule in self.rules:
            existing = current.get((rule['type'], rule['key']))
            if existing is None:
                self.added.append(rule)
            elif any(getattr(existing, column) != rule[column] for column in COMPARED_COLUMNS):
                self.replaced.append((existing, rule))
            else:
                self.unchanged += 1
        incoming = {(rule['type'], rule['key']) for rule in self.rules}
        self.removed = [rule for identity, rule in current.items() if identity not in incoming] \
            if mode == 'replace' else []

    def toDict(self) -> dict:
        return {
            'mode': self.mode,
            'added': [plannedRule(rule) for rule in self.added],
            'replaced': [{'rule': plannedRule(rule), 'current': serializeRule(existing)}
                         for existing, rule in self.replaced],
            'removed': [serializeRule(rule) for rule in self.removed],
            'unchanged': self.unchanged,
        }

    def apply(self) -> None:
        now = int(time.time())
        if self.removed:
            for rule in self.removed:
                self.fleet.baseline.rules.remove(rule)
            db.session.flush()
        applyRules(self.fleet, self.rules, 'replace', now)
        db.session.commit()
        rulesChanged(self.fleet)


def previewCopy(user, fleet_id: int, payloads: List[dict], mode: str) -> dict:
    return CopyPlan(ownedFleet(user, fleet_id), payloads, mode).toDict()


def copyRules(user, fleet_id: int, payloads: List[dict], mode: str) -> dict:
    fleet = ownedFleet(user, fleet_id)
    CopyPlan(fleet, payloads, mode).apply()
    return serializeBaseline(fleet)


def rulesChanged(fleet: Fleet) -> None:
    """Drift and health follow the new rules at once; servers missing content the rules now need are checked"""
    from application.models import baselineDrift
    baselineDrift.rulesChanged(fleet)
