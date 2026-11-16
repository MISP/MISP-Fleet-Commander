"""Baselines: rules are validated and normalised per type, secrets and server-specific settings are refused, and a
fleet's baseline is only reachable by the fleet's owner"""
import uuid

import pytest


def snapshot(settings):
    return {"query_result": {"serverSettings": {"finalSettings": [
        {"setting": name, "type": type, "value": value, **({"redacted": True} if redacted else {})}
        for name, type, value, redacted in settings
    ]}}}


SETTINGS = [
    ("MISP.live", "boolean", True, False),
    ("Security.password_policy_length", "numeric", 12, False),
    ("Session.timeout", "numeric", 60, False),
    ("MISP.footer_text", "string", "hello", False),
    ("Plugin.Custom_api_credential", "string", "*****", True),
]


@pytest.fixture(autouse=True)
def checks(monkeypatch):
    """Baseline checks handed to the workers, without running them"""
    from application.workers import tasks
    calls = []
    monkeypatch.setattr(tasks, "checkBaselineTask", lambda server_ids: calls.append(server_ids))
    return calls


@pytest.fixture()
def owner(db, make_user):
    from application import redisModel
    from application.DBModels import Fleet, Server
    user = make_user(f"baseline-{uuid.uuid4().hex[:8]}@test.test")
    fleets = []
    for name in ("Alpha", "Beta"):
        fleet = Fleet(name=name, description="", user_id=user.id, timestamp=1)
        db.session.add(fleet)
        fleets.append(fleet)
    db.session.commit()
    server = Server(name="baseline-misp", url="https://baseline-misp.test", user_id=user.id, fleet_id=fleets[0].id)
    server.authkey = "key"
    db.session.add(server)
    db.session.commit()
    redisModel.saveServerInfo(server.uuid, snapshot(SETTINGS))
    fleet_ids = [fleet.id for fleet in fleets]
    yield user, fleets
    dropBaselines(db, fleet_ids)


def dropBaselines(db, fleet_ids):
    """Other test files evaluate health for fleets by ID: leave no rules behind"""
    from application.DBModels import Baseline
    db.session.rollback()
    for baseline in Baseline.query.filter(Baseline.fleet_id.in_(fleet_ids)).all():
        db.session.delete(baseline)
    db.session.commit()


@pytest.fixture()
def api(client, auth_headers):
    class API:
        def __init__(self, user):
            self.headers = auth_headers(user)

        def get(self, path):
            return client.get(path, headers=self.headers)

        def post(self, path, body=None):
            return client.post(path, json=body if body is not None else {}, headers=self.headers)

        def put(self, path, body):
            return client.put(path, json=body, headers=self.headers)

        def delete(self, path):
            return client.delete(path, headers=self.headers)
    return API


def add(api, fleet, *rules, **options):
    return api.post(f"/baselines/fleet/{fleet.id}/rules", {"rules": list(rules), **options})


# Validation

GALAXY_UUID = "5165f976-6b17-4131-bcfc-652d1b11cc01"


@pytest.mark.parametrize("rule, expected", [
    ({"type": "setting", "key": "MISP.live", "expected": "1"}, {"expected": True, "comparator": "eq"}),
    ({"type": "setting", "key": "MISP.live", "expected": False}, {"expected": False}),
    ({"type": "setting", "key": "Security.password_policy_length", "expected": "16", "comparator": "gte"},
     {"expected": 16, "comparator": "gte"}),
    ({"type": "setting", "key": "Session.timeout", "expected": 30, "comparator": "lte", "severity": "critical"},
     {"expected": 30, "severity": "critical"}),
    ({"type": "setting", "key": "MISP.footer_text", "expected": 12}, {"expected": "12"}),
    # A setting no server reports is kept as given: the fleet may not have refreshed yet
    ({"type": "setting", "key": "Plugin.Unknown_setting", "expected": "x"}, {"expected": "x"}),
    ({"type": "setting", "key": "Plugin.Unknown_number", "expected": "2.5", "comparator": "gte"}, {"expected": 2.5}),
    ({"type": "taxonomy_enabled", "key": " tlp "}, {"key": "tlp", "expected": True, "label": ""}),
    ({"type": "taxonomy_enabled", "key": "PAP", "expected": "0"}, {"expected": False}),
    ({"type": "galaxy_enabled", "key": GALAXY_UUID.upper(), "expected": True},
     {"key": GALAXY_UUID}),
    ({"type": "object_template_active", "key": "cccdaaf6-c140-461c-8d1c-aa79bbd029e0", "expected": "true"},
     {"expected": True, "label": "abuseipdb"}),
    # MISP ships a few UUIDs in uppercase: keys are lowercased, and still find their name
    ({"type": "object_template_active", "key": "B7341729-5A8A-439F-A775-6D814DA3C7B5"},
     {"key": "b7341729-5a8a-439f-a775-6d814da3c7b5", "label": "btc-transaction"}),
    ({"type": "version_min", "key": "ignored", "expected": "v2.5"}, {"key": "", "expected": "2.5.0", "comparator": "gte"}),
    ({"type": "setting", "key": "MISP.baseurl", "expected": "https://x", "force": True}, {"forced": True}),
])
def test_valid_rules_are_normalised(owner, rule, expected):
    from application.models.baselines import FleetSettings, validateRule
    user, fleets = owner
    valid = validateRule(rule, FleetSettings(fleets[0]))
    for field, value in expected.items():
        assert valid[field] == value, field


@pytest.mark.parametrize("rule, field, code", [
    ("nope", None, None),
    ({"type": "registry", "key": "x"}, "type", None),
    ({"type": "setting", "expected": True}, "key", None),
    ({"type": "setting", "key": "live", "expected": True}, "key", None),
    ({"type": "setting", "key": "MISP.live", "expected": "maybe"}, "expected", None),
    ({"type": "setting", "key": "MISP.live", "expected": True, "comparator": "gte"}, "comparator", None),
    ({"type": "setting", "key": "MISP.footer_text", "expected": "a", "comparator": "lte"}, "comparator", None),
    ({"type": "setting", "key": "Security.password_policy_length", "expected": "12.5"}, "expected", None),
    ({"type": "setting", "key": "Plugin.Unknown_setting", "expected": {"a": 1}}, "expected", None),
    ({"type": "setting", "key": "Plugin.Unknown_setting", "expected": "x" * 9000}, "expected", None),
    ({"type": "setting", "key": "MISP.live", "expected": True, "severity": "high"}, "severity", None),
    ({"type": "setting", "key": "MISP.live", "expected": True, "note": "n" * 501}, "note", None),
    # Secrets: by name, or because MISP redacts them, even when forced
    ({"type": "setting", "key": "MISP.redis_password", "expected": "x", "force": True}, "key", "secret"),
    ({"type": "setting", "key": "Security.salt", "expected": "x", "force": True}, "key", "secret"),
    ({"type": "setting", "key": "Plugin.Custom_api_credential", "expected": "x"}, "key", "secret"),
    # Server-specific settings need `force`
    ({"type": "setting", "key": "MISP.baseurl", "expected": "https://x"}, "key", "server_specific"),
    ({"type": "setting", "key": "GnuPG.email", "expected": "a@b.c"}, "key", "server_specific"),
    ({"type": "taxonomy_enabled", "key": "has space"}, "key", None),
    ({"type": "galaxy_enabled", "key": "mitre-attack-pattern"}, "key", None),
    ({"type": "taxonomy_enabled", "key": "tlp", "comparator": "gte"}, "comparator", None),
    ({"type": "version_min", "expected": "latest"}, "expected", None),
])
def test_invalid_rules_are_refused(owner, rule, field, code):
    from application.models.baselines import BaselineError, FleetSettings, validateRule
    user, fleets = owner
    with pytest.raises(BaselineError) as error:
        validateRule(rule, FleetSettings(fleets[0]))
    assert error.value.field == field
    assert error.value.code == code


# API

def test_a_fleet_without_baseline_has_no_rules(owner, api):
    user, fleets = owner
    response = api(user).get(f"/baselines/fleet/{fleets[0].id}")
    assert response.status_code == 200
    assert response.get_json() == {"id": None, "fleet_id": fleets[0].id, "created": None, "updated": None, "rules": []}


def test_add_view_update_and_delete_rules(owner, api):
    user, fleets = owner
    client = api(user)
    response = add(client, fleets[0],
                   {"type": "setting", "key": "MISP.live", "expected": "1", "note": "Users need access"},
                   {"type": "taxonomy_enabled", "key": "tlp"},
                   {"type": "version_min", "expected": "2.5.20", "severity": "critical"})
    assert response.status_code == 201, response.get_json()
    baseline = response.get_json()
    assert baseline["id"] is not None and baseline["created"] is not None
    rules = baseline["rules"]
    assert [(r["type"], r["key"], r["expected"]) for r in rules] == [
        ("setting", "MISP.live", True), ("taxonomy_enabled", "tlp", True), ("version_min", "", "2.5.20")]
    assert [r["remediable"] for r in rules] == [True, True, False]
    assert client.get(f"/baselines/fleet/{fleets[0].id}").get_json() == baseline

    response = client.put(f"/baselines/rules/{rules[0]['id']}", {"expected": False, "severity": "info"})
    assert response.status_code == 200, response.get_json()
    assert response.get_json()["expected"] is False and response.get_json()["severity"] == "info"
    assert response.get_json()["note"] == "Users need access"
    response = client.put(f"/baselines/rules/{rules[0]['id']}", {"key": "MISP.disable_emailing"})
    assert response.status_code == 400 and response.get_json()["field"] == "key"
    response = client.put(f"/baselines/rules/{rules[0]['id']}", {"comparator": "gte"})
    assert response.status_code == 400 and response.get_json()["field"] == "comparator"

    assert client.delete(f"/baselines/rules/{rules[1]['id']}").status_code == 200
    response = client.post(f"/baselines/fleet/{fleets[0].id}/rules/delete", {"rule_ids": [rules[2]["id"]]})
    assert [r["id"] for r in response.get_json()["rules"]] == [rules[0]["id"]]
    response = client.post(f"/baselines/fleet/{fleets[0].id}/rules/delete", {"rule_ids": [rules[2]["id"]]})
    assert response.status_code == 404

    response = client.delete(f"/baselines/fleet/{fleets[0].id}")
    assert response.status_code == 200 and response.get_json()["id"] is None
    from application.DBModels import BaselineRule
    assert BaselineRule.query.filter_by(id=rules[0]["id"]).first() is None


def test_invalid_rules_are_all_listed_and_none_is_added(owner, api):
    user, fleets = owner
    client = api(user)
    response = add(client, fleets[0],
                   {"type": "taxonomy_enabled", "key": "tlp"},
                   {"type": "setting", "key": "MISP.baseurl", "expected": "x"},
                   {"type": "taxonomy_enabled", "key": "tlp", "expected": False},
                   {"type": "setting", "key": "Security.salt", "expected": "x"})
    assert response.status_code == 400
    errors = response.get_json()["errors"]
    assert [(e["index"], e["code"]) for e in errors] == [(1, "server_specific"), (2, "duplicate"), (3, "secret")]
    assert client.get(f"/baselines/fleet/{fleets[0].id}").get_json()["rules"] == []


def test_rules_already_in_the_baseline(owner, api):
    user, fleets = owner
    client = api(user)
    add(client, fleets[0], {"type": "taxonomy_enabled", "key": "tlp"})
    response = add(client, fleets[0], {"type": "taxonomy_enabled", "key": "tlp", "expected": False},
                   {"type": "taxonomy_enabled", "key": "pap"})
    assert response.status_code == 409
    assert response.get_json()["errors"][0]["index"] == 0

    response = add(client, fleets[0], {"type": "taxonomy_enabled", "key": "tlp", "expected": False},
                   {"type": "taxonomy_enabled", "key": "pap"}, on_conflict="skip")
    assert [(r["key"], r["expected"]) for r in response.get_json()["rules"]] == [("tlp", True), ("pap", True)]

    response = add(client, fleets[0], {"type": "taxonomy_enabled", "key": "tlp", "expected": False},
                   on_conflict="replace")
    assert [(r["key"], r["expected"]) for r in response.get_json()["rules"]] == [("tlp", False), ("pap", True)]

    assert add(client, fleets[0], {"type": "taxonomy_enabled", "key": "x"}, on_conflict="ignore").status_code == 400


def test_copy_a_baseline_from_another_fleet(owner, api):
    user, fleets = owner
    client = api(user)
    alpha, beta = fleets
    add(client, alpha, {"type": "taxonomy_enabled", "key": "tlp"},
        {"type": "setting", "key": "MISP.baseurl", "expected": "https://shared", "force": True})
    add(client, beta, {"type": "taxonomy_enabled", "key": "tlp", "expected": False},
        {"type": "taxonomy_enabled", "key": "pap"})

    response = client.post(f"/baselines/fleet/{beta.id}/copy", {"from_fleet_id": alpha.id, "mode": "merge"})
    assert response.status_code == 200, response.get_json()
    assert [(r["key"], r["expected"], r["forced"]) for r in response.get_json()["rules"]] == [
        ("tlp", True, False), ("pap", True, False), ("MISP.baseurl", "https://shared", True)]

    response = client.post(f"/baselines/fleet/{beta.id}/copy", {"from_fleet_id": alpha.id})
    assert [r["key"] for r in response.get_json()["rules"]] == ["tlp", "MISP.baseurl"]

    assert client.post(f"/baselines/fleet/{beta.id}/copy", {"from_fleet_id": beta.id}).status_code == 400
    assert client.post(f"/baselines/fleet/{beta.id}/copy", {"from_fleet_id": "1"}).status_code == 400
    assert client.post(f"/baselines/fleet/{beta.id}/copy", {"from_fleet_id": alpha.id, "mode": "x"}).status_code == 400
    client.delete(f"/baselines/fleet/{alpha.id}")
    response = client.post(f"/baselines/fleet/{beta.id}/copy", {"from_fleet_id": alpha.id})
    assert response.status_code == 400 and response.get_json()["field"] == "from_fleet_id"


def test_baselines_of_other_users_are_unknown(db, owner, api, make_user):
    from application.DBModels import Fleet
    user, fleets = owner
    add(api(user), fleets[0], {"type": "taxonomy_enabled", "key": "tlp"})
    rule_id = api(user).get(f"/baselines/fleet/{fleets[0].id}").get_json()["rules"][0]["id"]
    # Admins included: resources stay owned per user
    otherUser = make_user(f"other-{uuid.uuid4().hex[:8]}@test.test", is_admin=True)
    other = api(otherUser)
    assert other.get(f"/baselines/fleet/{fleets[0].id}").status_code == 404
    assert add(other, fleets[0], {"type": "taxonomy_enabled", "key": "pap"}).status_code == 404
    assert other.put(f"/baselines/rules/{rule_id}", {"expected": False}).status_code == 404
    assert other.delete(f"/baselines/rules/{rule_id}").status_code == 404
    assert other.delete(f"/baselines/fleet/{fleets[0].id}").status_code == 404
    assert other.post(f"/baselines/fleet/{fleets[0].id}/rules/delete", {"rule_ids": [rule_id]}).status_code == 404

    own = Fleet(name="Own", description="", user_id=otherUser.id, timestamp=1)
    db.session.add(own)
    db.session.commit()
    assert other.post(f"/baselines/fleet/{own.id}/copy", {"from_fleet_id": fleets[0].id}).status_code == 404
    assert api(user).get(f"/baselines/fleet/{fleets[0].id}").get_json()["rules"][0]["expected"] is True


def test_a_baseline_goes_with_its_fleet(db, owner, api):
    from application.DBModels import Baseline, BaselineRule
    user, fleets = owner
    baseline_id = add(api(user), fleets[1], {"type": "taxonomy_enabled", "key": "tlp"}).get_json()["id"]
    db.session.delete(fleets[1])
    db.session.commit()
    assert Baseline.query.get(baseline_id) is None
    assert BaselineRule.query.filter_by(baseline_id=baseline_id).count() == 0


def test_rule_types_for_the_editor(owner, api):
    user, fleets = owner
    body = api(user).get("/baselines/types").get_json()
    assert [t["type"] for t in body["types"]] == ["setting", "taxonomy_enabled", "galaxy_enabled",
                                                   "object_template_active", "version_min", "organisation",
                                                   "sharing_group", "custom_galaxy"]
    assert "MISP.baseurl" in body["server_specific_settings"] and body["server_specific_prefixes"] == ["GnuPG.", "SMIME."]
