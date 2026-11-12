"""Baseline drift: each rule is judged against a server's snapshot (match, drift or unknown), drifting rules become
health issues, and the fleet's drift matrix follows rule changes and content checks"""
import asyncio
import copy
import json
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_baselines import dropBaselines

FIXTURE = Path(__file__).parent / "fixtures" / "snapshot_misp_3.0.0.json"
SNAPSHOT = json.loads(FIXTURE.read_text())
GALAXY = "5165f976-6b17-4131-bcfc-652d1b11cc01"
TEMPLATE = "b7341729-5a8a-439f-a775-6d814da3c7b5"

TAXONOMIES = [{"Taxonomy": {"id": "1", "namespace": "tlp", "enabled": True}},
              {"Taxonomy": {"id": "2", "namespace": "pap", "enabled": False}}]
GALAXIES = [{"Galaxy": {"id": "155", "uuid": GALAXY, "name": "FireHOL IPsets", "namespace": "firehol-ipsets",
                        "type": "IPset", "enabled": True}}]
TEMPLATES = [{"ObjectTemplate": {"id": "26", "uuid": TEMPLATE.upper(), "name": "btc-transaction", "version": "4",
                                 "active": False}},
             {"ObjectTemplate": {"id": "402", "uuid": TEMPLATE.upper(), "name": "btc-transaction", "version": "5",
                                 "active": True}}]
CONTENT_ANSWERS = {
    "/taxonomies/index": TAXONOMIES,
    "/galaxies/index": GALAXIES,
    "/objectTemplates/index/all": TEMPLATES,
}


@pytest.fixture(autouse=True)
def checks(app, monkeypatch):
    from application.workers import tasks
    calls = []
    monkeypatch.setattr(tasks, "checkBaselineTask", lambda server_ids: calls.append(server_ids))
    return calls


def snapshotWith(settings=None, content=None):
    data = copy.deepcopy(SNAPSHOT)
    for entry in data["query_result"]["serverSettings"]["finalSettings"]:
        if settings and entry["setting"] in settings:
            entry["value"] = settings[entry["setting"]]
    if content is not None:
        data["query_result"]["baselineState"] = content
    return data


def okStatus(version="3.0.0"):
    import time
    return {"version": version, "_latency": 0.2, "_status_code": 200, "timestamp": int(time.time())}


def contentState(**answers):
    from application.models.baselineDrift import contentState as build
    types = ["taxonomy_enabled", "galaxy_enabled", "object_template_active"]
    urls = ["/taxonomies/index", "/galaxies/index", "/objectTemplates/index/all"]
    return build(types, [copy.deepcopy(answers.get(url, CONTENT_ANSWERS[url])) for url in urls], now=1)


# Values

@pytest.mark.parametrize("comparator, expected, actual, matches", [
    ("eq", True, True, True), ("eq", True, "1", True), ("eq", True, 1, True), ("eq", True, False, False),
    ("eq", False, "", True), ("eq", True, None, False),
    ("eq", 12, "12", True), ("eq", 12, 12.0, True), ("eq", 12, "x", False),
    ("eq", "abc", "abc", True), ("eq", "abc", "abd", False), ("eq", "", None, True), ("eq", None, "", True),
    ("eq", "1", True, True), ("eq", "60", 60, True),
    ("gte", 12, 14, True), ("gte", 12, "12", True), ("gte", 12, 8, False), ("gte", 12, "", False),
    ("lte", 60, 30, True), ("lte", 60, 61, False),
])
def test_values_compare_the_way_misp_stores_them(comparator, expected, actual, matches):
    from application.health.drift import compare
    assert compare(comparator, expected, actual) is matches


# Evaluation

def rule(id, type, key="", expected=True, comparator="eq", severity="warning", label="", note=""):
    return {"id": id, "type": type, "key": key, "expected": expected, "comparator": comparator,
            "severity": severity, "label": label, "note": note}


def evaluate(rules, snapshot, status=None):
    from application.health.drift import evaluate as run
    from application.health.engine import ServerState
    srv = SimpleNamespace(id=1, uuid="u", fleet_id=None, authkey="k")
    return {r.rule_id: r for r in run(rules, ServerState(srv, snapshot, status or okStatus()))}


def test_each_rule_type_is_judged():
    rules = [
        rule(1, "setting", "MISP.live", True),
        rule(2, "setting", "MISP.correlation_limit", 30, "gte"),
        rule(3, "setting", "Session.timeout", 60, "lte"),
        rule(4, "setting", "Plugin.Not_reported", "x"),
        rule(5, "setting", "MISP.redis_password", "x"),
        rule(6, "version_min", "", "2.5.20"),
        rule(7, "version_min", "", "3.1.0"),
        rule(8, "taxonomy_enabled", "tlp", True),
        rule(9, "taxonomy_enabled", "pap", True),
        rule(10, "taxonomy_enabled", "missing", False),
        rule(11, "galaxy_enabled", GALAXY, False),
        rule(12, "object_template_active", TEMPLATE, True),
        rule(13, "object_template_active", "00000000-0000-0000-0000-000000000000", True),
    ]
    results = evaluate(rules, snapshotWith({"MISP.correlation_limit": 20}, contentState()))
    states = {id: (r.state, r.actual) for id, r in results.items()}
    assert states == {
        1: ("match", True), 2: ("drift", 20), 3: ("match", 60), 4: ("unknown", None), 5: ("unknown", None),
        6: ("match", "3.0.0"), 7: ("drift", "3.0.0"),
        8: ("match", True), 9: ("drift", False), 10: ("match", None),
        11: ("drift", True), 12: ("match", True), 13: ("drift", None),
    }
    assert results[4].reason == "This MISP does not report this setting"
    assert results[5].reason == "MISP hides this setting's value"
    assert results[13].reason == "Not on this server"


def test_missing_data_is_unknown():
    rules = [rule(1, "setting", "MISP.live"), rule(2, "taxonomy_enabled", "tlp"), rule(3, "galaxy_enabled", GALAXY)]
    noDiagnostics = copy.deepcopy(SNAPSHOT)
    noDiagnostics["query_result"]["serverSettings"] = {"error": "Request timed out"}
    noDiagnostics["query_result"]["baselineState"] = contentState(**{"/galaxies/index": {"error": "Server unreachable"}})
    results = evaluate(rules, noDiagnostics)
    assert (results[1].state, results[1].reason) == ("unknown", "No diagnostics: Request timed out")
    assert results[2].state == "match"
    assert (results[3].state, results[3].reason) == ("unknown", "Could not list the galaxies: Server unreachable")

    results = evaluate(rules, copy.deepcopy(SNAPSHOT))
    assert (results[2].state, results[2].reason) == ("unknown", "Its taxonomies were not listed yet")


def test_content_state_keeps_errors_and_the_latest_template():
    state = contentState(**{"/taxonomies/index": {"_status_code": 403, "message": "Not allowed"},
                            "/galaxies/index": {"name": "not an index"}})
    assert state["taxonomies"] == {"error": "Could not list the taxonomies: HTTP 403: Not allowed"}
    assert state["galaxies"] == {"error": "Could not list the galaxies: unexpected answer"}
    assert state["objectTemplates"] == {"items": {TEMPLATE: {"enabled": True, "name": "btc-transaction"}}}
    assert contentState()["galaxies"]["items"][GALAXY] == {"enabled": True, "name": "firehol-ipsets :: FireHOL IPsets"}


# With the database: health issues, matrix, checks

@pytest.fixture()
def fleet(db, make_user):
    from application import redisModel
    from application.DBModels import Fleet, Server
    user = make_user(f"drift-{uuid.uuid4().hex[:8]}@test.test")
    theFleet = Fleet(name="Drift", description="", user_id=user.id, timestamp=1)
    db.session.add(theFleet)
    db.session.commit()
    servers = []
    for name in ("beta", "Alpha"):
        server = Server(name=f"{name}", url=f"https://{name}.test", user_id=user.id, fleet_id=theFleet.id)
        server.authkey = "key"
        db.session.add(server)
        servers.append(server)
    db.session.commit()
    for server in servers:
        redisModel.saveServerInfo(server.uuid, snapshotWith())
        redisModel.saveServerStatus(server.uuid, okStatus())
    fleet_id = theFleet.id
    yield user, theFleet, servers
    dropBaselines(db, [fleet_id])
    for server in servers:
        redisModel.deleteServerData(server.uuid, server.id)


def setStatus(server, status):
    from application import redisModel
    redisModel.saveServerStatus(server.uuid, status)


def addRules(client, headers, fleet, *rules):
    response = client.post(f"/baselines/fleet/{fleet.id}/rules", json={"rules": list(rules)}, headers=headers)
    assert response.status_code == 201, response.get_json()
    return response.get_json()["rules"]


def issues(client, headers, server):
    response = client.get(f"/health/issues?server_id={server.id}&include_acked=1", headers=headers)
    return [issue for issue in response.get_json() if issue["rule"] == "baseline_drift"]


def test_drifting_rules_are_health_issues(fleet, client, auth_headers):
    from application import redisModel
    user, theFleet, (beta, alpha) = fleet
    headers = auth_headers(user)
    for server in (beta, alpha):
        setStatus(server, okStatus())
    redisModel.saveServerInfo(beta.uuid, snapshotWith({"MISP.live": False}, contentState()))
    rules = addRules(client, headers, theFleet,
                     {"type": "setting", "key": "MISP.live", "expected": True, "severity": "critical",
                      "note": "Users must reach it"},
                     {"type": "taxonomy_enabled", "key": "pap"},
                     {"type": "galaxy_enabled", "key": GALAXY, "expected": True, "severity": "info"})

    found = {issue["id"]: issue for issue in issues(client, headers, beta)}
    assert sorted(found) == [f"baseline_drift:{beta.id}:{rules[0]['id']}", f"baseline_drift:{beta.id}:{rules[1]['id']}"]
    live = found[f"baseline_drift:{beta.id}:{rules[0]['id']}"]
    assert (live["severity"], live["category"], live["title"]) == ("critical", "config", "MISP.live differs from the baseline")
    assert live["detail"] == "Expected true, found false. Users must reach it"
    assert live["action"] == {"kind": "open_baseline", "rule_id": rules[0]["id"]}
    assert live["evidence"]["actual"] is False
    assert found[f"baseline_drift:{beta.id}:{rules[1]['id']}"]["title"] == "Taxonomy pap should be enabled"

    # Content never listed on alpha: unknown, no issue
    assert issues(client, headers, alpha) == []

    # An unreachable server reports that only
    setStatus(beta, {"error": "Server unreachable", "timestamp": okStatus()["timestamp"]})
    assert issues(client, headers, beta) == []


def test_unlisted_content_is_one_info_issue(fleet, client, auth_headers):
    from application import redisModel
    user, theFleet, (beta, alpha) = fleet
    headers = auth_headers(user)
    setStatus(beta, okStatus())
    redisModel.saveServerInfo(beta.uuid, snapshotWith(content=contentState(
        **{"/taxonomies/index": {"error": "Request timed out"}})))
    addRules(client, headers, theFleet, {"type": "taxonomy_enabled", "key": "tlp"})
    [issue] = issues(client, headers, beta)
    assert (issue["id"], issue["severity"]) == (f"baseline_drift:{beta.id}:unchecked", "info")
    assert issue["detail"] == "Could not list the taxonomies: Request timed out"


def test_drift_matrix(fleet, client, auth_headers, make_user):
    from application import redisModel
    user, theFleet, (beta, alpha) = fleet
    headers = auth_headers(user)
    redisModel.saveServerInfo(beta.uuid, snapshotWith({"MISP.live": False}, contentState()))
    redisModel.saveServerInfo(alpha.uuid, snapshotWith(content=contentState()))
    setStatus(beta, okStatus())
    setStatus(alpha, {"error": "Server unreachable", "timestamp": okStatus()["timestamp"]})
    rules = addRules(client, headers, theFleet, {"type": "setting", "key": "MISP.live", "expected": True},
                     {"type": "taxonomy_enabled", "key": "tlp"})

    body = client.get(f"/baselines/fleet/{theFleet.id}/drift", headers=headers).get_json()
    assert [r["id"] for r in body["rules"]] == [r["id"] for r in rules]
    assert [s["name"] for s in body["servers"]] == ["Alpha", "beta"]
    alphaRow, betaRow = body["servers"]
    live, tlp = str(rules[0]["id"]), str(rules[1]["id"])
    assert betaRow["results"][live] == {"state": "drift", "actual": False, "reason": ""}
    assert betaRow["results"][tlp]["state"] == "match"
    assert (betaRow["drift"], betaRow["unavailable"], betaRow["content_checked_at"]) == (1, None, 1)
    # Unreachable: last known values, but unknown
    assert alphaRow["unavailable"] == "Unreachable"
    assert alphaRow["results"][live] == {"state": "unknown", "actual": True, "stale": True,
                                         "reason": "Unreachable: last known value"}
    assert body["totals"] == {"match": 1, "drift": 1, "unknown": 2}

    other = auth_headers(make_user(f"other-{uuid.uuid4().hex[:8]}@test.test"))
    assert client.get(f"/baselines/fleet/{theFleet.id}/drift", headers=other).status_code == 404


def test_rule_changes_re_evaluate_and_check_missing_content(fleet, client, auth_headers, checks, monkeypatch):
    from application import redisModel
    import application.models.health as healthModel
    user, theFleet, (beta, alpha) = fleet
    headers = auth_headers(user)
    published = []
    monkeypatch.setattr(healthModel, "publishServerHealth", lambda server: published.append(server.id))
    redisModel.saveServerInfo(beta.uuid, snapshotWith(content=contentState()))

    addRules(client, headers, theFleet, {"type": "setting", "key": "MISP.live", "expected": True})
    assert sorted(published) == sorted([beta.id, alpha.id]) and checks == []

    # alpha never listed its taxonomies: it is checked; beta has them
    published.clear()
    addRules(client, headers, theFleet, {"type": "taxonomy_enabled", "key": "tlp"})
    assert checks == [[alpha.id]] and len(published) == 2

    response = client.post(f"/baselines/fleet/{theFleet.id}/check", headers=headers)
    assert response.status_code == 202 and sorted(response.get_json()["server_ids"]) == sorted([beta.id, alpha.id])
    assert sorted(checks[-1]) == sorted([beta.id, alpha.id])


def test_a_check_lists_content_and_names_rules(fleet, client, auth_headers, monkeypatch):
    from application import redisModel
    import application.models.utils as utils
    from application.models import baselineDrift
    user, theFleet, (beta, alpha) = fleet
    headers = auth_headers(user)
    requested = []

    async def fakeFetcher(server, urls, timeout=300):
        requested.append((server.id, urls))
        return [copy.deepcopy(CONTENT_ANSWERS[url]) for url in urls]
    monkeypatch.setattr(utils, "asyncFetcher", fakeFetcher)
    rules = addRules(client, headers, theFleet, {"type": "galaxy_enabled", "key": GALAXY},
                     {"type": "object_template_active", "key": TEMPLATE.upper()})
    assert rules[0]["label"] == ""  # FireHOL is not in the plugin's list

    redisModel.deleteServerData(alpha.uuid, alpha.id)
    outcomes = baselineDrift.checkServers([beta, alpha])
    assert outcomes == {beta.id: "checked", alpha.id: "never refreshed: a full refresh is needed"}
    assert requested == [(beta.id, ["/galaxies/index", "/objectTemplates/index/all"])]
    state = redisModel.getServerInfo(beta.uuid)["query_result"]["baselineState"]
    assert sorted(state) == ["galaxies", "objectTemplates", "timestamp"]
    body = client.get(f"/baselines/fleet/{theFleet.id}", headers=headers).get_json()
    assert [r["label"] for r in body["rules"]] == ["firehol-ipsets :: FireHOL IPsets", "btc-transaction"]


def test_full_refresh_lists_the_content_rules_need(fleet, client, auth_headers, monkeypatch):
    from application import redisModel
    import application.models.servers as serverModel
    user, theFleet, (beta, alpha) = fleet
    headers = auth_headers(user)
    answers = {
        "/servers/serverSettings/diagnostics/light:1": SNAPSHOT["query_result"]["serverSettings"],
        "/users/view/me": {"User": {"id": "1"}},
        "/servers/index": [],
        "/users/registrations": [],
        "/users/statistics": {"stats": {}},
        **CONTENT_ANSWERS,
    }
    requested = []

    async def fakeFetcher(server, urls, timeout=300):
        requested.extend(urls)
        return [copy.deepcopy(answers[url]) for url in urls]
    monkeypatch.setattr(serverModel, "asyncFetcher", fakeFetcher)
    monkeypatch.setattr(redisModel, "setServerWatchedTimestamp", lambda uuid: None)

    asyncio.run(serverModel.fetchServerInfoAsync(beta, {}))
    assert "/taxonomies/index" not in requested
    assert "baselineState" not in redisModel.getServerInfo(beta.uuid)["query_result"]

    addRules(client, headers, theFleet, {"type": "taxonomy_enabled", "key": "pap"})
    requested.clear()
    asyncio.run(serverModel.fetchServerInfoAsync(beta, {}))
    assert "/taxonomies/index" in requested and "/galaxies/index" not in requested
    state = redisModel.getServerInfo(beta.uuid)["query_result"]["baselineState"]
    assert state["taxonomies"]["items"] == {"tlp": {"enabled": True}, "pap": {"enabled": False}}
