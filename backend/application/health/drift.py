"""Baseline drift: how a server compares with each rule of its fleet's baseline, and the health issues that follow.

Settings are read from the snapshot's diagnostics and the version from the connection test, as for the other
rules. Taxonomies, galaxies and object templates come from `baselineState`, a compact listing the full refresh adds
to the snapshot when the fleet's baseline has rules of these types:

    {"timestamp": 1700000000,
     "taxonomies": {"items": {"tlp": {"enabled": true}}},
     "galaxies": {"items": {"<uuid>": {"enabled": true, "name": "…"}}},
     "objectTemplates": {"error": "Could not list the object templates: …"},
     "organisations": {"items": {"<uuid>": {"name": "…", "type": "", "nationality": "", "sector": "", "local": false}}},
     "sharingGroups": {"items": {"<uuid>": {"name": "…", "releasability": "", "description": "", "active": true,
                                            "roaming": false, "members": {"<org uuid>": {"name": "…", "extend": false}}}}},
     "customGalaxies": {"items": {"<uuid>": {"name": "…", "namespace": "…", "enabled": true,
                                             "clusters": {"<cluster uuid>": 1700000000}}}}}

Custom galaxies carry their clusters only when a rule asks for them (`clusters_error` when they could not be listed).

Each rule is `match`, `drift` or `unknown` (no data to judge, with the reason). Organisations, sharing groups and
custom galaxies say what differs in the reason of a drifting result. Unknown rules raise no issue, except one `info`
issue per server when part of the content could not be listed.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Optional

from application.health.engine import Finding, ServerState, rule, section_error
from application.health.versions import format_version, parse_version

MATCH, DRIFT, UNKNOWN = "match", "drift", "unknown"
STATES = (MATCH, DRIFT, UNKNOWN)

# Rule type → its section in `baselineState`
CONTENT_SECTIONS = {
    "taxonomy_enabled": "taxonomies",
    "galaxy_enabled": "galaxies",
    "object_template_active": "objectTemplates",
    "organisation": "organisations",
    "sharing_group": "sharingGroups",
    "custom_galaxy": "customGalaxies",
}
CONTENT_NOUNS = {
    "taxonomies": "taxonomies",
    "galaxies": "galaxies",
    "objectTemplates": "object templates",
    "organisations": "organisations",
    "sharingGroups": "sharing groups",
    "customGalaxies": "custom galaxies",
}
# Content checked as a whole item (present, and as described), not only as enabled or disabled
STRUCTURED_TYPES = ("organisation", "sharing_group", "custom_galaxy")
STRUCTURED_NOUNS = {"organisation": "Organisation", "sharing_group": "Sharing group", "custom_galaxy": "Custom galaxy"}
TRUE_WORDS = ("1", "true", "yes", "on")
FALSE_WORDS = ("0", "false", "no", "off", "")
COMPARATOR_WORDS = {"eq": "", "gte": "at least ", "lte": "at most "}
# Rule type → (noun, word when on, word when off)
CONTENT_WORDS = {
    "taxonomy_enabled": ("Taxonomy", "enabled", "disabled"),
    "galaxy_enabled": ("Galaxy", "enabled", "disabled"),
    "object_template_active": ("Object template", "active", "inactive"),
}


@dataclass
class RuleResult:
    rule_id: int
    state: str
    actual: Any = None
    reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# Value normalisation

def asBool(value) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str) and value.strip().lower() in TRUE_WORDS + FALSE_WORDS:
        return value.strip().lower() in TRUE_WORDS
    return None


def asNumber(value) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def sameValue(expected, actual) -> bool:
    """Equality the way MISP stores settings: `"1"`, `1` and `true` are the same boolean, `"12"` and `12` the same
    number, and an empty value is `null`"""
    if isinstance(expected, bool):
        return asBool(actual) is expected
    if isinstance(expected, (int, float)):
        number = asNumber(actual)
        return number is not None and number == float(expected)
    if expected is None or expected == "":
        return actual is None or actual == ""
    if isinstance(actual, bool):
        return asBool(expected) is actual
    if isinstance(actual, (int, float)):
        return asNumber(expected) == float(actual)
    return actual is not None and str(actual) == str(expected)


def compare(comparator: str, expected, actual) -> bool:
    if comparator in ("gte", "lte"):
        number, limit = asNumber(actual), asNumber(expected)
        if number is None or limit is None:
            return False
        return number >= limit if comparator == "gte" else number <= limit
    return sameValue(expected, actual)


# Evaluation

def settingEntries(state: ServerState) -> Optional[Dict[str, dict]]:
    settings = state.section("serverSettings")
    entries = settings.get("finalSettings") if isinstance(settings, dict) else None
    if not isinstance(entries, list):
        return None
    return {entry["setting"]: entry for entry in entries if isinstance(entry, dict) and "setting" in entry}


def currentVersion(state: ServerState) -> Optional[str]:
    snapshotVersion = state.server_settings.get("version")
    snapshotVersion = snapshotVersion if isinstance(snapshotVersion, dict) else {}
    return (state.status or {}).get("version") or snapshotVersion.get("current")


def evaluateSetting(baselineRule: dict, entries: Optional[Dict[str, dict]], state: ServerState) -> RuleResult:
    ruleId, key = baselineRule["id"], baselineRule["key"]
    if entries is None:
        error = section_error(state.query_result.get("serverSettings"))
        return RuleResult(ruleId, UNKNOWN, reason=f"No diagnostics: {error}" if error else "No diagnostics yet")
    entry = entries.get(key)
    if entry is None:
        return RuleResult(ruleId, UNKNOWN, reason="This MISP does not report this setting")
    if entry.get("redacted"):
        return RuleResult(ruleId, UNKNOWN, reason="MISP hides this setting's value")
    actual = entry.get("value")
    matches = compare(baselineRule.get("comparator") or "eq", baselineRule["expected"], actual)
    return RuleResult(ruleId, MATCH if matches else DRIFT, actual)


def evaluateVersion(baselineRule: dict, state: ServerState) -> RuleResult:
    current = parse_version(currentVersion(state))
    minimum = parse_version(baselineRule["expected"])
    if current is None:
        return RuleResult(baselineRule["id"], UNKNOWN, reason="Version unknown")
    if minimum is None:
        return RuleResult(baselineRule["id"], UNKNOWN, format_version(current), reason="Invalid minimum version")
    return RuleResult(baselineRule["id"], MATCH if current >= minimum else DRIFT, format_version(current))


def contentItems(baselineRule: dict, content: Optional[dict]):
    """The items of the rule's section, or the `unknown` result when they were not listed"""
    section = CONTENT_SECTIONS[baselineRule["type"]]
    data = content.get(section) if isinstance(content, dict) else None
    if not isinstance(data, dict):
        return RuleResult(baselineRule["id"], UNKNOWN, reason=f"Its {CONTENT_NOUNS[section]} were not listed yet")
    if data.get("error"):
        return RuleResult(baselineRule["id"], UNKNOWN, reason=str(data["error"]))
    return data.get("items") if isinstance(data.get("items"), dict) else {}


def evaluateContent(baselineRule: dict, content: Optional[dict]) -> RuleResult:
    ruleId, expected = baselineRule["id"], baselineRule["expected"] is not False
    items = contentItems(baselineRule, content)
    if isinstance(items, RuleResult):
        return items
    item = items.get(baselineRule["key"])
    if item is None:
        # Absent means not enabled: fine when the rule wants it disabled
        return RuleResult(ruleId, DRIFT if expected else MATCH, None, reason="Not on this server")
    actual = item.get("enabled") is True
    return RuleResult(ruleId, MATCH if actual == expected else DRIFT, actual)


def quoted(value) -> str:
    return f"`{value}`" if value not in (None, "") else "empty"


def textDifference(field: str, expected, actual) -> Optional[str]:
    """`name `b` instead of `a``, when a text the rule sets differs"""
    if expected in (None, "") or (actual or "") == expected:
        return None
    return f"{field} {quoted(actual)} instead of {quoted(expected)}"


def organisationDifferences(expected: dict, item: dict) -> List[str]:
    """What differs, in words. Fields the rule does not set are not checked"""
    differences = [textDifference(field, expected.get(field), item.get(field))
                   for field in ("name", "type", "nationality", "sector")]
    if "local" in expected and (item.get("local") is True) != expected["local"]:
        differences.append("local instead of external" if item.get("local") else "external instead of local")
    return [difference for difference in differences if difference]


def sharingGroupDifferences(expected: dict, item: dict) -> List[str]:
    differences = [textDifference(field, expected.get(field), item.get(field))
                   for field in ("name", "releasability", "description")]
    if "active" in expected and (item.get("active") is True) != expected["active"]:
        differences.append("inactive" if expected["active"] else "active")
    members = item.get("members") if isinstance(item.get("members"), dict) else {}
    missing = [member["name"] for member in expected.get("members") or [] if member["uuid"] not in members]
    if missing:
        shown = ", ".join(missing[:5]) + (f" and {len(missing) - 5} more" if len(missing) > 5 else "")
        differences.append(f"{len(missing)} member{'s' if len(missing) > 1 else ''} missing: {shown}")
    return [difference for difference in differences if difference]


def plural(count: int, noun: str) -> str:
    return f"{count} {noun}{'' if count == 1 else 's'}"


def evaluateStructured(baselineRule: dict, content: Optional[dict]) -> RuleResult:
    """Present and as the rule describes it. A drifting result says what differs in `reason`"""
    ruleId, kind, expected = baselineRule["id"], baselineRule["type"], baselineRule["expected"] or {}
    items = contentItems(baselineRule, content)
    if isinstance(items, RuleResult):
        return items
    item = items.get(baselineRule["key"])
    if not isinstance(item, dict):
        return RuleResult(ruleId, DRIFT, None, reason="Not on this server")

    if kind == "organisation":
        actual = {field: item.get(field) for field in ("name", "type", "nationality", "sector", "local")}
        differences = organisationDifferences(expected, item)
    elif kind == "sharing_group":
        members = item.get("members") if isinstance(item.get("members"), dict) else {}
        differences = sharingGroupDifferences(expected, item)
        actual = {field: item.get(field) for field in ("name", "releasability", "description", "active")}
        actual["members"] = len(members)
        actual["missing"] = sum(1 for member in expected.get("members") or [] if member["uuid"] not in members)
    else:
        if item.get("clusters_error"):
            return RuleResult(ruleId, UNKNOWN, reason=str(item["clusters_error"]))
        clusters = item.get("clusters")
        if not isinstance(clusters, dict):
            return RuleResult(ruleId, UNKNOWN, reason="Its clusters were not listed yet")
        wanted = expected.get("clusters") or {}
        missing = [uuid for uuid in wanted if uuid not in clusters]
        older = [uuid for uuid, version in wanted.items() if uuid in clusters and clusters[uuid] < version]
        enabled = item.get("enabled") is True
        actual = {"enabled": enabled, "clusters": len(clusters), "missing": len(missing), "older": len(older)}
        differences = ([] if enabled else ["disabled"]) + \
            ([f"{plural(len(missing), 'cluster')} missing"] if missing else []) + \
            ([f"{plural(len(older), 'cluster')} older than on the reference"] if older else [])
    if differences:
        reason = "; ".join(differences)
        return RuleResult(ruleId, DRIFT, actual, reason=reason[0].upper() + reason[1:])
    return RuleResult(ruleId, MATCH, actual)


def evaluate(rules: Iterable[dict], state: ServerState) -> List[RuleResult]:
    """One result per rule (rules as `serializeRule` returns them), in the rules' order"""
    entries = settingEntries(state)
    content = state.query_result.get("baselineState")
    results = []
    for baselineRule in rules:
        if baselineRule["type"] == "setting":
            results.append(evaluateSetting(baselineRule, entries, state))
        elif baselineRule["type"] == "version_min":
            results.append(evaluateVersion(baselineRule, state))
        elif baselineRule["type"] in STRUCTURED_TYPES:
            results.append(evaluateStructured(baselineRule, content))
        elif baselineRule["type"] in CONTENT_SECTIONS:
            results.append(evaluateContent(baselineRule, content))
        else:
            results.append(RuleResult(baselineRule["id"], UNKNOWN, reason="Unknown rule type"))
    return results


def contentErrors(rules: Iterable[dict], state: ServerState) -> Dict[str, str]:
    """Sections the rules need that could not be listed: section → error"""
    content = state.query_result.get("baselineState")
    content = content if isinstance(content, dict) else {}
    errors = {}
    for section in {CONTENT_SECTIONS[r["type"]] for r in rules if r["type"] in CONTENT_SECTIONS}:
        data = content.get(section)
        if isinstance(data, dict) and data.get("error"):
            errors[section] = str(data["error"])
    # A custom galaxy whose clusters could not be listed
    galaxies = content.get("customGalaxies")
    items = galaxies.get("items") if isinstance(galaxies, dict) and isinstance(galaxies.get("items"), dict) else {}
    for r in rules:
        item = items.get(r["key"]) if r["type"] == "custom_galaxy" else None
        if isinstance(item, dict) and item.get("clusters_error"):
            errors[f"customGalaxies:{r['key']}"] = str(item["clusters_error"])
    return errors


# Wording

def formatValue(value) -> str:
    if value is None or value == "":
        return "empty"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return f"`{value}`" if isinstance(value, str) else str(value)


def describe(baselineRule: dict, result: RuleResult) -> Finding:
    kind, key = baselineRule["type"], baselineRule["key"]
    name = baselineRule.get("label") or key
    expected = baselineRule["expected"]
    if kind == "setting":
        title = f"{key} differs from the baseline"
        detail = (f"Expected {COMPARATOR_WORDS.get(baselineRule.get('comparator'), '')}{formatValue(expected)}, "
                  f"found {formatValue(result.actual)}.")
    elif kind == "version_min":
        title = f"MISP older than the baseline's {expected}"
        detail = f"Running {result.actual}, the baseline asks for at least {expected}."
    elif kind in STRUCTURED_TYPES:
        noun = STRUCTURED_NOUNS[kind]
        if result.actual is None:
            title = f"{noun} {name} is missing"
            detail = "It is not on this server."
        else:
            title = f"{noun} {name} differs from the baseline"
            detail = f"{result.reason}."
    else:
        noun, on, off = CONTENT_WORDS[kind]
        title = f"{noun} {name} should be {on if expected else off}"
        detail = "It is not on this server." if result.actual is None else f"It is {on if result.actual else off}."
    if baselineRule.get("note"):
        detail += f" {baselineRule['note']}"
    return Finding(
        baselineRule.get("severity") or "warning", title, detail, subject=str(baselineRule["id"]),
        evidence={"rule_id": baselineRule["id"], "type": kind, "key": key,
                  # A sharing group's members or a galaxy's clusters would weigh on every issue
                  "expected": {"name": name} if kind in STRUCTURED_TYPES else expected,
                  "comparator": baselineRule.get("comparator") or "eq", "actual": result.actual},
        action={"kind": "open_baseline", "rule_id": baselineRule["id"]},
    )


# Health rule

def rulesFor(ctx, fleet_id: Optional[int]) -> List[dict]:
    """The fleet's baseline rules, read once per evaluation context"""
    if fleet_id is None:
        return []
    cache = ctx.baseline_rules
    if fleet_id not in cache:
        from application.models.baselines import serializedRulesOfFleet
        cache[fleet_id] = serializedRulesOfFleet(fleet_id)
    return cache[fleet_id]


@rule("baseline_drift", "config")
def baselineDrift(state, ctx):
    rules = rulesFor(ctx, getattr(state.server, "fleet_id", None))
    if not rules:
        return
    byId = {baselineRule["id"]: baselineRule for baselineRule in rules}
    for result in evaluate(rules, state):
        if result.state == DRIFT:
            yield describe(byId[result.rule_id], result)
    errors = contentErrors(rules, state)
    if errors:
        yield Finding("info", "Baseline partly unchecked",
                      " ".join(errors[section] for section in sorted(errors)),
                      subject="unchecked", evidence={"errors": errors}, action={"kind": "refresh"})
