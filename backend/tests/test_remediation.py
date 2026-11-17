"""Fixing baseline drift: the preview of what would change, the job it starts, and the unit that writes to MISP,
reads the values back and updates the server's snapshot"""
import copy

import pytest

from test_drift import (CONTENT_ANSWERS, GALAXY, TEMPLATE, addRules, checks, contentState, fleet, okStatus,  # noqa: F401
                        setStatus, snapshotWith)


class FakeMisp:
    """Settings and content of one MISP, through the mispOps calls the unit makes"""

    def __init__(self, settings=None, keeps=()):
        self.settings = dict(settings or {})
        self.keeps = set(keeps)  # settings MISP accepts but does not change
        self.answers = copy.deepcopy(CONTENT_ANSWERS)
        self.writes = []

    def getSetting(self, server, name):
        return self.settings.get(name)

    def editSetting(self, server, name, value):
        self.writes.append(("setting", name, value))
        if name not in self.keeps:
            self.settings[name] = value

    def listing(self, server, url, model, what):
        return [record[model] for record in copy.deepcopy(self.answers[url])]

    def setFlag(self, url, model, id, field, value):
        for record in self.answers[url]:
            if str(record[model]["id"]) == str(id):
                record[model][field] = value

    def setTaxonomyEnabled(self, server, id, enabled):
        self.writes.append(("taxonomy", id, enabled))
        self.setFlag("/taxonomies/index", "Taxonomy", id, "enabled", enabled)

    def setGalaxyEnabled(self, server, id, enabled):
        self.writes.append(("galaxy", id, enabled))
        self.setFlag("/galaxies/index", "Galaxy", id, "enabled", enabled)

    def toggleObjectTemplate(self, server, id):
        self.writes.append(("template", id))
        for record in self.answers["/objectTemplates/index/all"]:
            if str(record["ObjectTemplate"]["id"]) == str(id):
                record["ObjectTemplate"]["active"] = not record["ObjectTemplate"]["active"]


@pytest.fixture()
def misp(monkeypatch):
    from application.models import mispOps
    fake = FakeMisp()
    for name in ("getSetting", "editSetting", "listing", "setTaxonomyEnabled", "setGalaxyEnabled",
                 "toggleObjectTemplate"):
        monkeypatch.setattr(mispOps, name, getattr(fake, name))
    return fake


@pytest.fixture()
def published(monkeypatch):
    import application.models.health as healthModel
    calls = []
    monkeypatch.setattr(healthModel, "publishServerHealth", lambda server: calls.append(server.id))
    return calls


@pytest.fixture()
def queued(monkeypatch):
    from application.workers import tasks
    calls = []
    monkeypatch.setattr(tasks, "runJob", lambda job_id: calls.append(job_id))
    return calls


def withCliOnly(snapshot, name):
    for entry in snapshot["query_result"]["serverSettings"]["finalSettings"]:
        if entry["setting"] == name:
            entry["cli_only"] = True
    return snapshot


def driftingFleet(client, headers, theFleet, beta, alpha):
    """beta drifts on four rules (two fixable), alpha cannot be reached"""
    from application import redisModel
    content = contentState(**{"/taxonomies/index": [{"Taxonomy": {"id": "2", "namespace": "pap", "enabled": False}}]})
    redisModel.saveServerInfo(beta.uuid, withCliOnly(snapshotWith(
        {"MISP.live": False, "Session.timeout": 90}, content), "Session.timeout"))
    setStatus(beta, okStatus())
    setStatus(alpha, {"error": "Server unreachable", "timestamp": okStatus()["timestamp"]})
    return addRules(client, headers, theFleet,
                    {"type": "setting", "key": "MISP.live", "expected": True, "severity": "critical"},
                    {"type": "setting", "key": "Session.timeout", "expected": 60, "comparator": "lte"},
                    {"type": "taxonomy_enabled", "key": "pap"},
                    {"type": "taxonomy_enabled", "key": "tlp"},
                    {"type": "version_min", "expected": "3.1.0"},
                    {"type": "setting", "key": "MISP.correlation_limit", "expected": 20})


def preview(client, headers, theFleet, **body):
    response = client.post(f"/baselines/fleet/{theFleet.id}/remediation/preview", json=body, headers=headers)
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def test_preview_lists_what_would_change(fleet, client, auth_headers, published):
    user, theFleet, (beta, alpha) = fleet
    headers = auth_headers(user)
    live, timeout, pap, tlp, version, correlation = driftingFleet(client, headers, theFleet, beta, alpha)

    body = preview(client, headers, theFleet)
    assert body["excluded"] == [{"id": alpha.id, "name": "Alpha", "reason": "Unreachable"}]
    [server] = body["servers"]
    items = {item["rule_id"]: item for item in server["items"]}
    assert sorted(items) == sorted([live["id"], timeout["id"], pap["id"], tlp["id"], version["id"]])
    assert (items[live["id"]]["action"], items[live["id"]]["current"], items[live["id"]]["expected"]) == ("apply", False, True)
    assert items[pap["id"]]["action"] == "apply"
    assert items[timeout["id"]]["action"] == "manual"
    assert items[timeout["id"]]["reason"] == "MISP only lets this setting change from its command line"
    assert items[version["id"]]["reason"] == "Upgrade MISP on this server"
    assert items[tlp["id"]]["action"] == "manual" and items[tlp["id"]]["current"] is None
    assert body["counts"] == {"apply": 2, "manual": 3, "servers": 1}

    # Narrowed: one rule, one cell
    assert [i["rule_id"] for i in preview(client, headers, theFleet, rule_ids=[pap["id"]])["servers"][0]["items"]] == [pap["id"]]
    cell = preview(client, headers, theFleet, items=[{"server_id": beta.id, "rule_id": live["id"]}])
    assert [i["rule_id"] for i in cell["servers"][0]["items"]] == [live["id"]] and cell["excluded"] == []
    assert preview(client, headers, theFleet, server_ids=[alpha.id])["servers"] == []
    bad = client.post(f"/baselines/fleet/{theFleet.id}/remediation/preview", json={"items": [{"server_id": "x"}]},
                      headers=headers)
    assert bad.status_code == 400


def test_confirming_starts_a_job_with_each_servers_rules(fleet, client, auth_headers, make_user, published, queued):
    import uuid
    from application.DBModels import Job
    user, theFleet, (beta, alpha) = fleet
    headers = auth_headers(user)
    live, timeout, pap, tlp, version, correlation = driftingFleet(client, headers, theFleet, beta, alpha)
    items = [{"server_id": beta.id, "rule_id": rule["id"]} for rule in (live, timeout, pap, version)]
    items.append({"server_id": alpha.id, "rule_id": live["id"]})

    response = client.post(f"/baselines/fleet/{theFleet.id}/remediation", json={"items": items}, headers=headers)
    assert response.status_code == 202, response.get_json()
    body = response.get_json()
    assert queued == [body["job_id"]]
    assert body["job"]["kind"] == "baseline_remediation" and body["job"]["title"] == "Fix 2 baseline values on beta"
    assert [r["server_id"] for r in body["job"]["results"]] == [beta.id]
    job = Job.query.get(body["job_id"])
    planned = job.secret_params["servers"][str(beta.id)]
    assert [(p["rule_id"], p["expected"]) for p in planned] == [(live["id"], True), (pap["id"], True)]

    # Only manual fixes left: nothing to start
    response = client.post(f"/baselines/fleet/{theFleet.id}/remediation",
                           json={"items": [{"server_id": beta.id, "rule_id": version["id"]}]}, headers=headers)
    assert response.status_code == 409
    other = auth_headers(make_user(f"other-{uuid.uuid4().hex[:8]}@test.test"))
    assert client.post(f"/baselines/fleet/{theFleet.id}/remediation", json={"items": items},
                       headers=other).status_code == 404


def test_confirming_by_servers_and_rules(fleet, client, auth_headers, published, queued, monkeypatch):
    """A whole fleet can drift on more values than `items` takes: the preview's servers and rules start the fix"""
    from application.DBModels import Job
    import application.models.baselineRemediation as remediation
    user, theFleet, (beta, alpha) = fleet
    headers = auth_headers(user)
    live, timeout, pap, tlp, version, correlation = driftingFleet(client, headers, theFleet, beta, alpha)
    url = f"/baselines/fleet/{theFleet.id}/remediation"
    monkeypatch.setattr(remediation, "MAX_ITEMS", 1)

    tooMany = [{"server_id": beta.id, "rule_id": live["id"]}, {"server_id": beta.id, "rule_id": pap["id"]}]
    assert client.post(url, json={"items": tooMany}, headers=headers).status_code == 400

    # Only the rules named: `MISP.live` stays out
    response = client.post(url, json={"server_ids": [beta.id, alpha.id], "rule_ids": [pap["id"], timeout["id"]]},
                           headers=headers)
    assert response.status_code == 202, response.get_json()
    planned = Job.query.get(response.get_json()["job_id"]).secret_params["servers"]
    assert list(planned) == [str(beta.id)]
    assert [p["rule_id"] for p in planned[str(beta.id)]] == [pap["id"]]

    for body in ({"server_ids": [beta.id]}, {"server_ids": [], "rule_ids": [pap["id"]]}, {"rule_ids": "all"}, {}):
        assert client.post(url, json=body, headers=headers).status_code == 400, body


def test_the_unit_fixes_checks_and_updates_the_snapshot(fleet, client, auth_headers, misp, published):
    from application.models.baselineRemediation import remediationUnit
    user, theFleet, (beta, alpha) = fleet
    headers = auth_headers(user)
    live, timeout, pap, tlp, version, correlation = driftingFleet(client, headers, theFleet, beta, alpha)
    misp.settings = {"MISP.live": False, "MISP.correlation_limit": "20", "Security.password_policy_length": "8"}
    misp.keeps = {"Security.password_policy_length"}
    misp.answers["/taxonomies/index"][1]["Taxonomy"]["enabled"] = False
    plan = [
        {"rule_id": live["id"], "type": "setting", "key": "MISP.live", "label": "", "comparator": "eq", "expected": True},
        {"rule_id": correlation["id"], "type": "setting", "key": "MISP.correlation_limit", "label": "",
         "comparator": "eq", "expected": 20},
        {"rule_id": 999, "type": "setting", "key": "Security.password_policy_length", "label": "",
         "comparator": "gte", "expected": 14},
        {"rule_id": pap["id"], "type": "taxonomy_enabled", "key": "pap", "label": "", "comparator": "eq", "expected": True},
        {"rule_id": 998, "type": "galaxy_enabled", "key": "00000000-0000-0000-0000-000000000000", "label": "",
         "comparator": "eq", "expected": True},
        {"rule_id": 997, "type": "object_template_active", "key": TEMPLATE, "label": "btc", "comparator": "eq",
         "expected": False},
    ]
    published.clear()
    unit = remediationUnit(beta, {"servers": {str(beta.id): plan}})

    outcomes = {o["rule_id"]: o for o in unit.response["rules"]}
    assert outcomes[live["id"]]["status"] == "fixed" and (outcomes[live["id"]]["before"], outcomes[live["id"]]["after"]) == (False, True)
    assert outcomes[correlation["id"]]["status"] == "already"
    assert outcomes[999]["status"] == "error"
    assert outcomes[999]["message"] == "MISP accepted the change but still reports `8`"
    assert ("setting", "Security.password_policy_length", 14) in misp.writes
    # The values before are kept, named, and only secrets would be hidden
    from application.models.jobs import redact
    assert {"key": "Security.password_policy_length", "value": "8"} in redact(unit.before)
    assert outcomes[pap["id"]]["status"] == "fixed" and outcomes[pap["id"]]["after"] is True
    assert outcomes[998] == {**outcomes[998], "status": "error", "message": "Not on this server"}
    assert outcomes[997]["status"] == "fixed" and outcomes[997]["after"] is False
    assert unit.ok is False
    assert unit.summary.startswith("3 fixed, 1 already as expected, 2 failed")
    assert ("setting", "MISP.correlation_limit", 20) not in misp.writes
    assert published == [beta.id]

    # Drift follows at once: the snapshot holds what was read back
    body = client.get(f"/baselines/fleet/{theFleet.id}/drift", headers=headers).get_json()
    beta_row = next(server for server in body["servers"] if server["id"] == beta.id)
    assert beta_row["results"][str(live["id"])]["state"] == "match"
    assert beta_row["results"][str(pap["id"])]["state"] == "match"

    assert remediationUnit(alpha, {"servers": {str(beta.id): plan}}).status == "skipped"


def test_a_remediation_job_runs_end_to_end(fleet, client, auth_headers, misp, published, queued):
    import application.models.jobRunner as jobRunner
    user, theFleet, (beta, alpha) = fleet
    headers = auth_headers(user)
    live, *_ = driftingFleet(client, headers, theFleet, beta, alpha)
    misp.settings = {"MISP.live": False}
    response = client.post(f"/baselines/fleet/{theFleet.id}/remediation",
                           json={"items": [{"server_id": beta.id, "rule_id": live["id"]}]}, headers=headers)
    job = jobRunner.run(response.get_json()["job_id"])
    assert (job.status, job.succeeded) == ("done", 1)
    [result] = job.results
    assert result.summary == "1 fixed" and result.before == [{"key": "MISP.live", "value": False}]
    assert misp.settings["MISP.live"] is True
