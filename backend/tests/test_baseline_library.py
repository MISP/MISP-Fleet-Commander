"""Saved baselines and presets: a user keeps named sets of rules (taken from a fleet or picked on a reference server)
and copies them, or the shipped presets, into fleets. They are only ever copied, never checked against servers"""
import os
import uuid

import pytest

from test_baselines import add, api, checks, owner  # noqa: F401

TLP = {"type": "taxonomy_enabled", "key": "tlp"}
PAP = {"type": "taxonomy_enabled", "key": "PAP"}
FORCED = {"type": "setting", "key": "MISP.baseurl", "expected": "https://shared", "force": True}


@pytest.fixture(autouse=True)
def noSavedBaselinesLeft(db):
    yield
    from application.DBModels import Baseline
    db.session.rollback()
    for baseline in Baseline.query.filter(Baseline.fleet_id.is_(None)).all():
        db.session.delete(baseline)
    db.session.commit()


def save(client, **body):
    return client.post("/baselines/saved", body)


def keys(rules):
    return [rule["key"] for rule in rules]


# Presets

def test_every_preset_is_valid_without_a_fleet(app):
    from application.models import baselineLibrary
    presets = baselineLibrary.presets()
    assert set(presets) >= {"security-hardening", "sharing-essentials"}
    files = [name for name in os.listdir(baselineLibrary.PRESETS_DIR) if name.endswith(".json")]
    assert len(presets) == len(files), "every preset file has a valid ID"
    for presetId, data in presets.items():
        assert data["name"] and data["description"], presetId
        valid = baselineLibrary.checkPreset(data)
        assert len(valid) == len(data["rules"]), presetId
        # Shipped as they validate: copying one changes nothing but the fleet's coercions
        for given, rule in zip(data["rules"], valid):
            assert rule["type"] == given["type"] and rule["key"] == given.get("key", ""), presetId
            assert not rule["forced"], presetId


def test_a_preset_cannot_hold_server_bound_rules(app):
    from application.models.baselineLibrary import checkPreset
    from application.models.baselines import BaselineError
    galaxy = {"type": "custom_galaxy", "key": str(uuid.uuid4()),
              "expected": {"name": "x", "source_server_id": 1, "clusters": {}}}
    with pytest.raises(BaselineError):
        checkPreset({"rules": [galaxy]})
    with pytest.raises(BaselineError):
        checkPreset({"rules": [FORCED]})


def test_library_lists_presets_and_own_saved_baselines(owner, api):
    user, fleets = owner
    client = api(user)
    library = client.get("/baselines/library").get_json()
    assert library["saved"] == []
    hardening = next(item for item in library["presets"] if item["id"] == "security-hardening")
    assert hardening["kind"] == "preset" and hardening["rule_count"] > 10
    assert hardening["types"]["setting"] > 10 and hardening["types"]["version_min"] == 1
    assert "rules" not in hardening
    assert [(item["name"], item["rule_count"]) for item in library["fleets"]] == [("Alpha", 0), ("Beta", 0)]
    assert [(item["name"], item["fleet_name"]) for item in library["servers"]] == [("baseline-misp", "Alpha")]

    detail = client.get("/baselines/presets/security-hardening").get_json()
    assert len(detail["rules"]) == hardening["rule_count"]
    assert detail["rules"][0]["id"] is None and "remediable" in detail["rules"][0]
    assert client.get("/baselines/presets/nope").status_code == 404


# Saving

def test_save_a_fleets_baseline(owner, api):
    from application.models.baselines import serializedRulesOfFleet
    user, (alpha, beta) = owner
    client = api(user)
    add(client, alpha, TLP, FORCED)

    response = save(client, name="  Lab   defaults ", description="For labs", from_fleet_id=alpha.id)
    assert response.status_code == 201, response.get_json()
    saved = response.get_json()
    assert saved["kind"] == "saved" and saved["name"] == "Lab defaults" and saved["description"] == "For labs"
    assert [(r["key"], r["forced"]) for r in saved["rules"]] == [("tlp", False), ("MISP.baseurl", True)]
    assert saved["types"] == {"taxonomy_enabled": 1, "setting": 1}
    # Copies: the fleet keeps its own rules, and the saved ones are never evaluated as a fleet's
    assert keys(serializedRulesOfFleet(alpha.id)) == ["tlp", "MISP.baseurl"]
    assert {r["id"] for r in saved["rules"]}.isdisjoint({r["id"] for r in serializedRulesOfFleet(alpha.id)})
    library = client.get("/baselines/library").get_json()
    assert [item["name"] for item in library["saved"]] == ["Lab defaults"]
    assert [(item["id"], item["rule_count"]) for item in library["fleets"]] == [(alpha.id, 2), (beta.id, 0)]

    taken = save(client, name="lab DEFAULTS", from_fleet_id=alpha.id)
    assert taken.status_code == 409 and taken.get_json()["code"] == "name_taken"
    assert save(client, name=" ", from_fleet_id=alpha.id).get_json()["field"] == "name"
    assert save(client, name="x" * 121, from_fleet_id=alpha.id).status_code == 400
    assert save(client, name="Empty", from_fleet_id=beta.id).get_json()["code"] == "empty_source"
    # Without rules: an empty one, filled rule by rule
    empty = save(client, name="Nothing yet")
    assert empty.status_code == 201 and empty.get_json()["rules"] == []


def test_save_rules_picked_on_a_reference_server(db, owner, api, make_user):
    from application.DBModels import Server
    user, (alpha, _) = owner
    client = api(user)
    server = Server.query.filter_by(fleet_id=alpha.id).first()
    rules = [{"type": "setting", "key": "Security.password_policy_length", "expected": "14", "comparator": "gte"},
             {"type": "setting", "key": "MISP.live", "expected": "1"}, TLP]

    response = save(client, name="From the reference", rules=rules, server_id=server.id)
    assert response.status_code == 201, response.get_json()
    # The reference server's setting types are used
    assert [r["expected"] for r in response.get_json()["rules"]] == [14, True, True]

    # Without a server, values stay as given until copied into a fleet
    response = save(client, name="Untyped", rules=rules[:1])
    assert response.get_json()["rules"][0]["expected"] == 14

    invalid = save(client, name="Invalid", rules=[TLP, {"type": "setting", "key": "nope"}])
    assert invalid.status_code == 400 and invalid.get_json()["errors"][0]["index"] == 1
    assert save(client, name="Secret", rules=[{"type": "setting", "key": "Plugin.Custom_api_credential",
                                               "expected": "x"}], server_id=server.id).status_code == 400
    assert save(client, name="Unknown server", rules=[TLP], server_id=999999).status_code == 404
    other = make_user(f"lib-other-{uuid.uuid4().hex[:8]}@test.test")
    assert save(api(other), name="Not mine", rules=[TLP], server_id=server.id).status_code == 404


def test_rename_describe_and_retake_a_saved_baseline(owner, api):
    user, (alpha, beta) = owner
    client = api(user)
    add(client, alpha, TLP)
    add(client, beta, PAP, FORCED)
    first = save(client, name="First", from_fleet_id=alpha.id).get_json()
    save(client, name="Second", from_fleet_id=alpha.id)

    response = client.put(f"/baselines/saved/{first['id']}", {"name": "Renamed", "description": "Now described"})
    assert response.status_code == 200
    assert (response.get_json()["name"], response.get_json()["description"]) == ("Renamed", "Now described")
    assert keys(response.get_json()["rules"]) == ["tlp"]
    assert client.put(f"/baselines/saved/{first['id']}", {"name": "second"}).status_code == 409
    # Its own name, in another case, is not taken
    assert client.put(f"/baselines/saved/{first['id']}", {"name": "RENAMED"}).status_code == 200

    response = client.put(f"/baselines/saved/{first['id']}", {"from_fleet_id": beta.id})
    assert [(r["key"], r["forced"]) for r in response.get_json()["rules"]] == [("PAP", False), ("MISP.baseurl", True)]
    assert client.get(f"/baselines/saved/{first['id']}").get_json()["rule_count"] == 2

    assert client.delete(f"/baselines/saved/{first['id']}").status_code == 200
    assert client.get(f"/baselines/saved/{first['id']}").status_code == 404
    assert [item["name"] for item in client.get("/baselines/library").get_json()["saved"]] == ["Second"]


def test_saved_baselines_of_other_users_are_unknown(db, owner, api, make_user):
    from application.DBModels import Fleet
    user, (alpha, _) = owner
    add(api(user), alpha, TLP)
    saved = save(api(user), name="Mine", from_fleet_id=alpha.id).get_json()
    rule_id = saved["rules"][0]["id"]

    otherUser = make_user(f"lib-admin-{uuid.uuid4().hex[:8]}@test.test", is_admin=True)
    other = api(otherUser)
    own = Fleet(name="Own", description="", user_id=otherUser.id, timestamp=1)
    db.session.add(own)
    db.session.commit()
    assert other.get(f"/baselines/saved/{saved['id']}").status_code == 404
    assert other.put(f"/baselines/saved/{saved['id']}", {"name": "Taken over"}).status_code == 404
    assert other.delete(f"/baselines/saved/{saved['id']}").status_code == 404
    assert other.post(f"/baselines/fleet/{own.id}/copy", {"from_saved_id": saved["id"]}).status_code == 404
    assert other.get("/baselines/library").get_json()["saved"] == []
    # The same name is free for another user
    add(other, own, TLP)
    assert save(other, name="Mine", from_fleet_id=own.id).status_code == 201
    # The rule routes reach a saved baseline's rules for its owner only
    assert other.put(f"/baselines/rules/{rule_id}", {"expected": False}).status_code == 404
    assert other.delete(f"/baselines/rules/{rule_id}").status_code == 404
    assert other.post(f"/baselines/saved/{saved['id']}/rules", {"rules": [PAP]}).status_code == 404
    assert api(user).get(f"/baselines/saved/{saved['id']}").get_json()["rules"][0]["expected"] is True


# Editing a saved baseline directly

def test_edit_a_saved_baseline_rule_by_rule(owner, api, checks):
    from application.models.baselines import serializedRulesOfFleet
    user, (alpha, _) = owner
    client = api(user)
    saved = save(client, name="Edited here").get_json()
    path = f"/baselines/saved/{saved['id']}/rules"

    # Setting values take the types the user's servers report (MISP.live is a boolean on the fleet's server)
    response = client.post(path, {"rules": [TLP, {"type": "setting", "key": "MISP.live", "expected": "1"}]})
    assert response.status_code == 201, response.get_json()
    rules = response.get_json()["rules"]
    assert [(r["key"], r["expected"]) for r in rules] == [("tlp", True), ("MISP.live", True)]
    assert response.get_json()["rule_count"] == 2

    conflict = client.post(path, {"rules": [{**TLP, "expected": False}]})
    assert conflict.status_code == 409 and conflict.get_json()["errors"][0]["rule_id"] == rules[0]["id"]
    replaced = client.post(path, {"rules": [{**TLP, "expected": False}], "on_conflict": "replace"})
    assert replaced.get_json()["rules"][0]["expected"] is False
    assert client.post(path, {"rules": [TLP], "on_conflict": "x"}).status_code == 400
    secret = {"type": "setting", "key": "Plugin.Custom_api_credential", "expected": "x"}
    invalid = client.post(path, {"rules": [secret]})
    assert invalid.status_code == 400 and invalid.get_json()["errors"][0]["code"] == "secret"

    response = client.put(f"/baselines/rules/{rules[1]['id']}", {"expected": "0", "severity": "critical"})
    assert response.status_code == 200, response.get_json()
    assert (response.get_json()["expected"], response.get_json()["severity"]) == (False, "critical")
    assert client.put(f"/baselines/rules/{rules[1]['id']}", {"key": "MISP.other"}).status_code == 400

    assert client.delete(f"/baselines/rules/{rules[0]['id']}").status_code == 200
    detail = client.get(f"/baselines/saved/{saved['id']}").get_json()
    assert [(r["key"], r["expected"], r["severity"]) for r in detail["rules"]] == [("MISP.live", False, "critical")]
    # Never evaluated: no fleet gets its rules, no server is checked for them
    assert serializedRulesOfFleet(alpha.id) == [] and checks == []

    # An empty saved baseline has nothing to import
    client.delete(f"/baselines/rules/{rules[1]['id']}")
    response = client.post(f"/baselines/fleet/{alpha.id}/copy/preview", {"from_saved_id": saved["id"]})
    assert response.status_code == 400 and response.get_json()["code"] == "empty_source"


def test_saved_baselines_go_with_their_user(db, make_user, api):
    from application.DBModels import Baseline, BaselineRule, Fleet
    user = make_user(f"lib-gone-{uuid.uuid4().hex[:8]}@test.test")
    fleet = Fleet(name="Gone", description="", user_id=user.id, timestamp=1)
    db.session.add(fleet)
    db.session.commit()
    add(api(user), fleet, TLP)
    saved_id = save(api(user), name="Gone", from_fleet_id=fleet.id).get_json()["id"]
    rule_ids = [rule.id for rule in Baseline.query.get(saved_id).rules]
    db.session.delete(fleet)
    db.session.delete(user)
    db.session.commit()
    assert Baseline.query.get(saved_id) is None
    assert BaselineRule.query.filter(BaselineRule.id.in_(rule_ids)).count() == 0


# Copying into a fleet

def test_copy_a_saved_baseline_with_a_preview(owner, api):
    user, (alpha, beta) = owner
    client = api(user)
    add(client, alpha, TLP, {"type": "setting", "key": "Session.timeout", "expected": 30, "comparator": "lte"})
    saved = save(client, name="Source", from_fleet_id=alpha.id).get_json()
    add(client, beta, {**TLP}, {"type": "setting", "key": "Session.timeout", "expected": 60, "comparator": "lte"},
        PAP)
    before = {r["key"]: r["id"] for r in client.get(f"/baselines/fleet/{beta.id}").get_json()["rules"]}

    response = client.post(f"/baselines/fleet/{beta.id}/copy/preview", {"from_saved_id": saved["id"]})
    assert response.status_code == 200, response.get_json()
    preview = response.get_json()
    assert preview["source"] == {"kind": "saved", "id": saved["id"], "name": "Source"}
    assert preview["mode"] == "replace"
    assert preview["added"] == [] and preview["unchanged"] == 1
    assert [(item["rule"]["expected"], item["current"]["expected"]) for item in preview["replaced"]] == [(30, 60)]
    assert keys(preview["removed"]) == ["PAP"]
    merge = client.post(f"/baselines/fleet/{beta.id}/copy/preview",
                        {"from_saved_id": saved["id"], "mode": "merge"}).get_json()
    assert merge["removed"] == [] and len(merge["replaced"]) == 1
    # A preview changes nothing
    assert client.get(f"/baselines/fleet/{beta.id}").get_json()["rules"][1]["expected"] == 60

    response = client.post(f"/baselines/fleet/{beta.id}/copy", {"from_saved_id": saved["id"]})
    assert response.status_code == 200, response.get_json()
    rules = response.get_json()["rules"]
    assert [(r["key"], r["expected"]) for r in rules] == [("tlp", True), ("Session.timeout", 30)]
    # Rules kept keep their ID (and their drift issues and acknowledgements)
    assert {r["key"]: r["id"] for r in rules} == {k: v for k, v in before.items() if k != "PAP"}


def test_copy_a_preset(owner, api, checks):
    from application.models.baselineLibrary import presets
    user, (alpha, _) = owner
    client = api(user)
    add(client, alpha, {"type": "taxonomy_enabled", "key": "circl"})
    expected = presets()["sharing-essentials"]["rules"]

    preview = client.post(f"/baselines/fleet/{alpha.id}/copy/preview", {"from_preset": "sharing-essentials"})
    assert preview.status_code == 200
    assert len(preview.get_json()["added"]) == len(expected) and keys(preview.get_json()["removed"]) == ["circl"]
    assert preview.get_json()["source"]["kind"] == "preset"

    response = client.post(f"/baselines/fleet/{alpha.id}/copy", {"from_preset": "sharing-essentials"})
    assert response.status_code == 200, response.get_json()
    assert keys(response.get_json()["rules"]) == [rule["key"] for rule in expected]
    # Servers are checked for the content the new rules need
    assert checks
    merged = client.post(f"/baselines/fleet/{alpha.id}/copy", {"from_preset": "security-hardening", "mode": "merge"})
    assert len(merged.get_json()["rules"]) == len(expected) + len(presets()["security-hardening"]["rules"])


@pytest.mark.parametrize("body, status, field", [
    ({}, 400, "from_fleet_id"),
    ({"from_preset": "sharing-essentials", "from_saved_id": 1}, 400, "from_fleet_id"),
    ({"from_preset": "unknown"}, 404, None),
    ({"from_preset": ["sharing-essentials"]}, 404, None),
    ({"from_saved_id": "1"}, 404, None),
    ({"from_saved_id": 999999}, 404, None),
    ({"from_preset": "sharing-essentials", "mode": "x"}, 400, "mode"),
])
def test_copy_needs_one_known_source(owner, api, body, status, field):
    user, (alpha, _) = owner
    for path in ("copy", "copy/preview"):
        response = api(user).post(f"/baselines/fleet/{alpha.id}/{path}", body)
        assert response.status_code == status, (path, response.get_json())
        assert response.get_json().get("field") == field


def test_copied_rules_are_validated_against_the_target_fleet(owner, api):
    """A saved value kept as given is coerced to the type the fleet's servers report, or refused"""
    user, (alpha, _) = owner
    client = api(user)
    saved = save(client, name="Loose", rules=[{"type": "setting", "key": "MISP.live", "expected": "maybe"}])
    assert saved.status_code == 201
    response = client.post(f"/baselines/fleet/{alpha.id}/copy/preview", {"from_saved_id": saved.get_json()["id"]})
    assert response.status_code == 400 and response.get_json()["errors"][0]["index"] == 0
