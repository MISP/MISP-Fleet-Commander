"""Health API: issues and summary scoped to the user's servers, filters, acknowledgements, and the HEALTH_UPDATED
event sent whenever a server's data changes"""
import asyncio
import copy
import json
import time
from pathlib import Path

import pytest

SNAPSHOT = json.loads((Path(__file__).parent / "fixtures" / "snapshot_misp_3.0.0.json").read_text())
LATEST = "v2.5.51"
START = 2_000_000_000


@pytest.fixture()
def clock(monkeypatch):
    """A controllable `time.time()`: acknowledgements and first-seen times depend on it"""
    now = [START]
    monkeypatch.setattr(time, "time", lambda: now[0])
    return now


@pytest.fixture(autouse=True)
def _latest_release(app, monkeypatch):
    import application.health.versions as versions
    monkeypatch.setattr(versions, "latest_release", lambda *args, **kwargs: LATEST)


@pytest.fixture()
def emitted(monkeypatch):
    from application.controllers.websocket import socketEmitter
    events = []
    monkeypatch.setattr(socketEmitter.socketio, "emit",
                        lambda event, data=None, **kw: events.append((event, data, kw.get("to"))))
    return events


def healthEvents(events):
    return [(data, room) for event, data, room in events if event == "HEALTH_UPDATED"]


def freshSnapshot(now):
    data = copy.deepcopy(SNAPSHOT)
    data["timestamp"] = now
    return data


def okStatus(now):
    return {"version": "3.0.0", "_latency": 0.2, "_status_code": 200, "timestamp": now}


def failedStatus(now):
    return {"error": "Connection refused", "timestamp": now}


@pytest.fixture()
def fleet(db, make_user, clock, emitted):
    """alice: `down` (unreachable) in fleet A, `up` (reachable, fresh snapshot) in fleet B, and an empty fleet C.
    bob: `bobs` (unreachable)"""
    from application import redisModel
    from application.DBModels import Fleet, HealthAck, Server

    alice, bob = make_user("health-alice@test.local"), make_user("health-bob@test.local")
    fleets = {}
    for name, user in (("A", alice), ("B", alice), ("C", alice), ("bob", bob)):
        fleets[name] = Fleet(name=f"Fleet {name}", description="", user_id=user.id, timestamp=1)
        db.session.add(fleets[name])
    db.session.commit()
    servers = {}
    for name, user, fleetName in (("down", alice, "A"), ("up", alice, "B"), ("bobs", bob, "bob")):
        servers[name] = Server(name=name, url=f"https://{name}.test", authkey="k" * 40,
                               fleet_id=fleets[fleetName].id, user_id=user.id)
        db.session.add(servers[name])
    db.session.commit()
    now = clock[0]
    for name, status in (("down", failedStatus(now)), ("up", okStatus(now)), ("bobs", failedStatus(now))):
        redisModel.saveServerInfo(servers[name].uuid, freshSnapshot(now))
        redisModel.saveServerStatus(servers[name].uuid, status)
    emitted.clear()

    class Fleet_:
        pass
    data = Fleet_()
    data.alice, data.bob, data.fleets, data.servers = alice, bob, fleets, servers
    yield data

    HealthAck.query.filter(HealthAck.user_id.in_([alice.id, bob.id])).delete(synchronize_session=False)
    for server in servers.values():
        if server in db.session:
            db.session.delete(server)
    db.session.commit()
    for fleetModel in fleets.values():
        db.session.delete(fleetModel)
    db.session.commit()


def get(client, auth_headers, user, path):
    response = client.get(path, headers=auth_headers(user))
    return response.status_code, response.get_json()


def expectedIssueIDs(server, now):
    from application.health import Context, evaluate_server
    return {issue.id for issue in evaluate_server(server, Context(now=now, latest_release=LATEST))}


# --- Issues -----------------------------------------------------------------------------------------------------------

def test_issues_are_scoped_to_the_users_servers(client, auth_headers, fleet, clock):
    status, issues = get(client, auth_headers, fleet.alice, "/health/issues")
    assert status == 200
    down, up, bobs = fleet.servers["down"], fleet.servers["up"], fleet.servers["bobs"]
    assert {issue["id"] for issue in issues} == expectedIssueIDs(down, clock[0]) | expectedIssueIDs(up, clock[0])
    assert {issue["server_id"] for issue in issues} == {down.id, up.id}
    assert bobs.id not in {issue["server_id"] for issue in issues}

    status, bobIssues = get(client, auth_headers, fleet.bob, "/health/issues")
    assert {issue["server_id"] for issue in bobIssues} == {bobs.id}


def test_issue_fields(client, auth_headers, fleet, clock):
    _, issues = get(client, auth_headers, fleet.alice, "/health/issues")
    unreachable = next(issue for issue in issues if issue["id"] == f"unreachable:{fleet.servers['down'].id}")
    assert unreachable["severity"] == "critical" and unreachable["category"] == "availability"
    assert unreachable["server_name"] == "down" and unreachable["fleet_name"] == "Fleet A"
    assert unreachable["server_url"] == "https://down.test"
    assert unreachable["fleet_id"] == fleet.fleets["A"].id
    assert unreachable["first_seen"] == clock[0] and unreachable["ack"] is None


def test_issues_are_sorted_by_severity_then_age(client, auth_headers, fleet, clock):
    from application.health import SEVERITIES
    get(client, auth_headers, fleet.alice, "/health/issues")
    # A new issue appears later: it keeps its own first-seen time, and order is by severity, then age
    clock[0] += 600
    from application import redisModel
    redisModel.saveServerStatus(fleet.servers["up"].uuid, dict(okStatus(clock[0]), _latency=5.0))
    _, issues = get(client, auth_headers, fleet.alice, "/health/issues")
    keys = [(SEVERITIES.index(issue["severity"]), issue["first_seen"]) for issue in issues]
    assert keys == sorted(keys)
    slow = next(issue for issue in issues if issue["rule"] == "slow")
    assert slow["first_seen"] == clock[0]


@pytest.mark.parametrize("query, check", [
    ("severity=critical", lambda issue, fleet: issue["severity"] == "critical"),
    ("severity=warning,info", lambda issue, fleet: issue["severity"] in ("warning", "info")),
    ("category=availability", lambda issue, fleet: issue["category"] == "availability"),
    ("fleet_id={B}", lambda issue, fleet: issue["server_id"] == fleet.servers["up"].id),
    ("server_id={down}", lambda issue, fleet: issue["server_id"] == fleet.servers["down"].id),
    ("severity=critical&fleet_id={A}", lambda issue, fleet: issue["id"] == f"unreachable:{fleet.servers['down'].id}"),
])
def test_issue_filters(client, auth_headers, fleet, query, check):
    query = query.format(A=fleet.fleets["A"].id, B=fleet.fleets["B"].id, down=fleet.servers["down"].id)
    status, issues = get(client, auth_headers, fleet.alice, f"/health/issues?{query}")
    assert status == 200 and issues
    assert all(check(issue, fleet) for issue in issues)


def test_empty_fleet_has_no_issues(client, auth_headers, fleet):
    status, issues = get(client, auth_headers, fleet.alice, f"/health/issues?fleet_id={fleet.fleets['C'].id}")
    assert status == 200 and issues == []


@pytest.mark.parametrize("query, expected", [
    ("severity=bogus", 400), ("category=bogus", 400), ("severity=critical,bogus", 400),
    ("fleet_id=abc", 400), ("fleet_id={bobFleet}", 404), ("fleet_id=999999", 404),
    ("server_id={bobServer}", 404), ("server_id=999999", 404),
])
def test_invalid_issue_filters(client, auth_headers, fleet, query, expected):
    query = query.format(bobFleet=fleet.fleets["bob"].id, bobServer=fleet.servers["bobs"].id)
    status, body = get(client, auth_headers, fleet.alice, f"/health/issues?{query}")
    assert status == expected and body["message"]


def test_health_requires_authentication(client, fleet):
    assert client.get("/health/issues").status_code == 401
    assert client.get("/health/summary").status_code == 401
    assert client.post("/health/ack", json={"issue_id": "unreachable:1"}).status_code == 401
    assert client.delete("/health/ack/unreachable:1").status_code == 401
    assert client.post("/health/ack/bulk", json={"issue_ids": ["unreachable:1"]}).status_code == 401
    assert client.post("/health/unack/bulk", json={"issue_ids": ["unreachable:1"]}).status_code == 401


# --- Summary ----------------------------------------------------------------------------------------------------------

def test_summary(client, auth_headers, fleet, clock):
    _, issues = get(client, auth_headers, fleet.alice, "/health/issues")
    status, summary = get(client, auth_headers, fleet.alice, "/health/summary")
    assert status == 200
    for severity in ("critical", "warning", "info"):
        assert summary["totals"][severity] == len([i for i in issues if i["severity"] == severity])
    down, up = fleet.servers["down"], fleet.servers["up"]
    assert summary["servers"] == {
        str(down.id): {"name": "down", "fleet_id": fleet.fleets["A"].id, "worst": "critical"},
        str(up.id): {"name": "up", "fleet_id": fleet.fleets["B"].id,
                     "worst": _worst([i for i in issues if i["server_id"] == up.id])},
    }
    assert summary["fleets"][str(fleet.fleets["A"].id)] == {"critical": 1, "warning": 0, "info": 0}
    assert summary["fleets"][str(fleet.fleets["C"].id)] == {"critical": 0, "warning": 0, "info": 0}
    assert str(fleet.fleets["bob"].id) not in summary["fleets"]
    assert summary["server_count"] == 2 and summary["acknowledged"] == 0
    assert summary["oldest_refresh"] == summary["newest_refresh"] == START
    assert summary["evaluated_at"] == clock[0]


def _worst(issues):
    from application.health import SEVERITIES
    return min((issue["severity"] for issue in issues), key=SEVERITIES.index) if issues else None


def test_summary_of_a_user_without_servers(client, auth_headers, make_user):
    status, summary = get(client, auth_headers, make_user("health-nobody@test.local"), "/health/summary")
    assert status == 200
    assert summary["totals"] == {"critical": 0, "warning": 0, "info": 0}
    assert summary["servers"] == {} and summary["server_count"] == 0 and summary["oldest_refresh"] is None


# --- Acknowledgements -------------------------------------------------------------------------------------------------

def ack(client, auth_headers, user, issue_id, **fields):
    response = client.post("/health/ack", json={"issue_id": issue_id, **fields}, headers=auth_headers(user))
    return response.status_code, response.get_json()


def visibleIDs(client, auth_headers, user, query=""):
    _, issues = get(client, auth_headers, user, f"/health/issues{query}")
    return {issue["id"] for issue in issues}


def test_acknowledged_issue_is_hidden(client, auth_headers, fleet, clock):
    issueID = f"unreachable:{fleet.servers['down'].id}"
    _, before = get(client, auth_headers, fleet.alice, "/health/summary")
    status, body = ack(client, auth_headers, fleet.alice, issueID, note="Planned maintenance")
    assert status == 200
    assert body["id"] == issueID and body["ack"] == {"until": None, "note": "Planned maintenance", "created": clock[0]}

    assert issueID not in visibleIDs(client, auth_headers, fleet.alice)
    _, withAcked = get(client, auth_headers, fleet.alice, "/health/issues?include_acked=1")
    acked = next(issue for issue in withAcked if issue["id"] == issueID)
    assert acked["ack"]["note"] == "Planned maintenance"

    _, summary = get(client, auth_headers, fleet.alice, "/health/summary")
    assert summary["acknowledged"] == 1
    assert summary["totals"]["critical"] == before["totals"]["critical"] - 1
    assert summary["servers"][str(fleet.servers["down"].id)]["worst"] is None
    assert summary["fleets"][str(fleet.fleets["A"].id)]["critical"] == 0


def test_acknowledgement_expires(client, auth_headers, fleet, clock):
    issueID = f"unreachable:{fleet.servers['down'].id}"
    assert ack(client, auth_headers, fleet.alice, issueID, until=clock[0] + 3600)[0] == 200
    clock[0] += 3599
    assert issueID not in visibleIDs(client, auth_headers, fleet.alice)
    clock[0] += 1
    assert issueID in visibleIDs(client, auth_headers, fleet.alice)


def test_acknowledgement_ends_when_the_issue_clears_and_comes_back(client, auth_headers, fleet, clock):
    from application import redisModel
    down = fleet.servers["down"]
    issueID = f"unreachable:{down.id}"
    assert ack(client, auth_headers, fleet.alice, issueID)[0] == 200

    clock[0] += 60
    redisModel.saveServerStatus(down.uuid, okStatus(clock[0]))
    assert issueID not in visibleIDs(client, auth_headers, fleet.alice, "?include_acked=1")  # Cleared

    clock[0] += 60
    redisModel.saveServerStatus(down.uuid, failedStatus(clock[0]))
    assert issueID in visibleIDs(client, auth_headers, fleet.alice)  # Back: the acknowledgement no longer applies


def test_acknowledging_again_updates_the_acknowledgement(client, auth_headers, fleet, clock):
    from application.DBModels import HealthAck
    issueID = f"unreachable:{fleet.servers['down'].id}"
    ack(client, auth_headers, fleet.alice, issueID, note="first")
    clock[0] += 10
    status, body = ack(client, auth_headers, fleet.alice, issueID, note="second", until=clock[0] + 60)
    assert status == 200 and body["ack"] == {"until": clock[0] + 60, "note": "second", "created": clock[0]}
    assert HealthAck.query.filter_by(user_id=fleet.alice.id, issue_id=issueID).count() == 1


def test_unacknowledge(client, auth_headers, fleet):
    issueID = f"unreachable:{fleet.servers['down'].id}"
    ack(client, auth_headers, fleet.alice, issueID)
    assert client.delete(f"/health/ack/{issueID}", headers=auth_headers(fleet.bob)).status_code == 404
    response = client.delete(f"/health/ack/{issueID}", headers=auth_headers(fleet.alice))
    assert response.status_code == 200 and response.get_json() == {"issue_id": issueID}
    assert issueID in visibleIDs(client, auth_headers, fleet.alice)
    assert client.delete(f"/health/ack/{issueID}", headers=auth_headers(fleet.alice)).status_code == 404


def test_issue_ids_with_a_subject_can_be_unacknowledged(client, auth_headers, fleet):
    _, issues = get(client, auth_headers, fleet.alice, f"/health/issues?server_id={fleet.servers['up'].id}")
    withSubject = [issue for issue in issues if issue["subject"] is not None]
    if not withSubject:
        pytest.skip("The fixture has no issue with a subject")
    issueID = withSubject[0]["id"]
    assert ack(client, auth_headers, fleet.alice, issueID)[0] == 200
    assert client.delete(f"/health/ack/{issueID}", headers=auth_headers(fleet.alice)).status_code == 200


@pytest.mark.parametrize("payload, expected", [
    ({}, 400),
    ({"issue_id": 12}, 400),
    ({"issue_id": "garbage"}, 404),
    ({"issue_id": "unreachable:{bobs}"}, 404),            # Someone else's server
    ({"issue_id": "unreachable:{up}"}, 404),              # Not a current issue
    ({"issue_id": "unreachable:999999"}, 404),
    ({"issue_id": "unreachable:{down}", "until": "tomorrow"}, 400),
    ({"issue_id": "unreachable:{down}", "until": True}, 400),
    ({"issue_id": "unreachable:{down}", "until": START - 1}, 400),
    ({"issue_id": "unreachable:{down}", "until": START}, 400),
    ({"issue_id": "unreachable:{down}", "note": 5}, 400),
    ({"issue_id": "unreachable:{down}", "note": "x" * 501}, 400),
])
def test_invalid_acknowledgements(client, auth_headers, fleet, payload, expected):
    from application.DBModels import HealthAck
    ids = {name: server.id for name, server in fleet.servers.items()}
    if isinstance(payload.get("issue_id"), str):
        payload = dict(payload, issue_id=payload["issue_id"].format(**ids))
    response = client.post("/health/ack", json=payload, headers=auth_headers(fleet.alice))
    assert response.status_code == expected and response.get_json()["message"]
    assert HealthAck.query.filter_by(user_id=fleet.alice.id).count() == 0


# --- Bulk acknowledgements --------------------------------------------------------------------------------------------

def bulk(client, auth_headers, user, path, payload):
    response = client.post(path, json=payload, headers=auth_headers(user))
    return response.status_code, response.get_json()


def serverOf(issue_id):
    return int(issue_id.split(":")[1])


def test_bulk_acknowledgement_hides_issues_across_servers(client, auth_headers, fleet, clock, emitted):
    _, issues = get(client, auth_headers, fleet.alice, "/health/issues")
    issueIDs = [issue["id"] for issue in issues]
    serverIDs = {serverOf(issueID) for issueID in issueIDs}
    assert len(issueIDs) > 1 and fleet.servers["down"].id in serverIDs

    until = clock[0] + 3600
    status, body = bulk(client, auth_headers, fleet.alice, "/health/ack/bulk",
                        {"issue_ids": issueIDs, "until": until, "note": "  Known drift  "})
    assert status == 200
    assert [issue["id"] for issue in body["acknowledged"]] == issueIDs
    assert all(issue["ack"] == {"until": until, "note": "Known drift", "created": clock[0]} for issue in body["acknowledged"])
    assert body["skipped"] == []
    assert visibleIDs(client, auth_headers, fleet.alice) == set()
    _, summary = get(client, auth_headers, fleet.alice, "/health/summary")
    assert summary["acknowledged"] == len(issueIDs)

    # One update per server, each carrying the acknowledgements
    events = healthEvents(emitted)
    assert sorted(payload["server_id"] for payload, _ in events) == sorted(serverIDs)
    assert all(room == f"user:{fleet.alice.id}" for _, room in events)
    assert all(issue["ack"] is not None for payload, _ in events for issue in payload["issues"])

    clock[0] += 3600  # Expired. The issues themselves may have changed meanwhile (e.g. a snapshot getting stale)
    assert get(client, auth_headers, fleet.alice, "/health/summary")[1]["acknowledged"] == 0


def test_bulk_acknowledgement_skips_what_it_cannot_acknowledge(client, auth_headers, fleet):
    from application.DBModels import HealthAck
    down, up, bobs = (fleet.servers[name].id for name in ("down", "up", "bobs"))
    issueIDs = [f"unreachable:{down}", f"unreachable:{bobs}", f"unreachable:{up}", "garbage", "unreachable:999999",
                f"unreachable:{down}"]
    status, body = bulk(client, auth_headers, fleet.alice, "/health/ack/bulk", {"issue_ids": issueIDs})
    assert status == 200
    assert [issue["id"] for issue in body["acknowledged"]] == [f"unreachable:{down}"]
    assert body["acknowledged"][0]["ack"]["until"] is None
    assert body["skipped"] == [
        {"issue_id": f"unreachable:{bobs}", "message": "Unknown issue"},
        {"issue_id": f"unreachable:{up}", "message": "This issue is not current: it may have cleared since"},
        {"issue_id": "garbage", "message": "Unknown issue"},
        {"issue_id": "unreachable:999999", "message": "Unknown issue"},
    ]
    assert [ack.issue_id for ack in HealthAck.query.filter_by(user_id=fleet.alice.id)] == [f"unreachable:{down}"]
    assert HealthAck.query.filter_by(server_id=bobs).count() == 0


def test_bulk_acknowledgement_updates_existing_acknowledgements(client, auth_headers, fleet, clock):
    from application.DBModels import HealthAck
    issueID = f"unreachable:{fleet.servers['down'].id}"
    ack(client, auth_headers, fleet.alice, issueID, note="first", until=clock[0] + 60)
    clock[0] += 10
    status, body = bulk(client, auth_headers, fleet.alice, "/health/ack/bulk", {"issue_ids": [issueID], "note": "second"})
    assert status == 200 and body["acknowledged"][0]["ack"] == {"until": None, "note": "second", "created": clock[0]}
    assert HealthAck.query.filter_by(user_id=fleet.alice.id, issue_id=issueID).count() == 1


def test_bulk_acknowledgement_of_nothing_current_publishes_nothing(client, auth_headers, fleet, emitted):
    status, body = bulk(client, auth_headers, fleet.alice, "/health/ack/bulk",
                        {"issue_ids": [f"unreachable:{fleet.servers['up'].id}"]})
    assert status == 200 and body["acknowledged"] == [] and len(body["skipped"]) == 1
    assert healthEvents(emitted) == []


@pytest.mark.parametrize("path", ["/health/ack/bulk", "/health/unack/bulk"])
@pytest.mark.parametrize("payload", [
    None,
    [],
    {},
    {"issue_ids": "unreachable:{down}"},
    {"issue_ids": []},
    {"issue_ids": [12]},
    {"issue_ids": ["unreachable:{down}", None]},
    {"issue_ids": [f"unreachable:{i}" for i in range(10_001)]},
])
def test_invalid_bulk_requests(client, auth_headers, fleet, path, payload):
    from application.DBModels import HealthAck
    if isinstance(payload, dict) and isinstance(payload.get("issue_ids"), list):
        payload = {"issue_ids": [i.format(down=fleet.servers["down"].id) if isinstance(i, str) else i
                                 for i in payload["issue_ids"]]}
    response = client.post(path, json=payload, headers=auth_headers(fleet.alice))
    assert response.status_code == 400 and response.get_json()["message"]
    assert HealthAck.query.filter_by(user_id=fleet.alice.id).count() == 0


@pytest.mark.parametrize("fields", [
    {"until": "tomorrow"},
    {"until": True},
    {"until": START},
    {"note": 5},
    {"note": "x" * 501},
])
def test_invalid_bulk_acknowledgement_fields(client, auth_headers, fleet, fields):
    from application.DBModels import HealthAck
    payload = {"issue_ids": [f"unreachable:{fleet.servers['down'].id}"], **fields}
    status, body = bulk(client, auth_headers, fleet.alice, "/health/ack/bulk", payload)
    assert status == 400 and body["message"]
    assert HealthAck.query.filter_by(user_id=fleet.alice.id).count() == 0


def test_bulk_unacknowledgement(client, auth_headers, fleet, emitted):
    _, issues = get(client, auth_headers, fleet.alice, "/health/issues")
    issueIDs = [issue["id"] for issue in issues]
    bulk(client, auth_headers, fleet.alice, "/health/ack/bulk", {"issue_ids": issueIDs})
    bobsID = f"unreachable:{fleet.servers['bobs'].id}"
    bulk(client, auth_headers, fleet.bob, "/health/ack/bulk", {"issue_ids": [bobsID]})
    emitted.clear()

    status, body = bulk(client, auth_headers, fleet.alice, "/health/unack/bulk",
                        {"issue_ids": issueIDs + [bobsID, "garbage"]})
    assert status == 200
    assert body["unacknowledged"] == issueIDs
    assert body["skipped"] == [{"issue_id": bobsID, "message": "This issue is not acknowledged"},
                               {"issue_id": "garbage", "message": "This issue is not acknowledged"}]
    assert visibleIDs(client, auth_headers, fleet.alice) == set(issueIDs)
    assert bobsID not in visibleIDs(client, auth_headers, fleet.bob)  # Bob's acknowledgement is untouched

    events = healthEvents(emitted)
    assert sorted(payload["server_id"] for payload, _ in events) == sorted({serverOf(i) for i in issueIDs})
    assert all(issue["ack"] is None for payload, _ in events for issue in payload["issues"])


# --- Live updates -----------------------------------------------------------------------------------------------------

def test_connection_test_publishes_health_to_the_owner(fleet, emitted, clock):
    import application.models.servers as serverModel
    down = fleet.servers["down"]
    clock[0] += 60
    serverModel.recordConnectionTest(down, okStatus(clock[0]))

    (payload, room), = healthEvents(emitted)
    assert room == f"user:{fleet.alice.id}"
    assert payload["server_id"] == down.id and payload["fleet_id"] == fleet.fleets["A"].id
    assert f"unreachable:{down.id}" not in {issue["id"] for issue in payload["issues"]}
    assert {issue["id"] for issue in payload["issues"]} == expectedIssueIDs(down, clock[0])


def test_full_refresh_publishes_health_once_everything_is_saved(monkeypatch, fleet, emitted, clock):
    import application.models.servers as serverModel
    from application import redisModel
    up = fleet.servers["up"]
    clock[0] += 3 * 3600  # The stored snapshot is now stale
    assert any(i.startswith("stale:") for i in expectedIssueIDs(up, clock[0]))
    answers = {
        "/servers/serverSettings/diagnostics/light:1": SNAPSHOT["query_result"]["serverSettings"],
        "/users/view/me": SNAPSHOT["query_result"]["serverUser"],
        "/servers/index": [],
        "/users/registrations": [],
        "/users/statistics": {"stats": {}},
    }
    seenAtPublish = []

    async def fakeFetcher(server, urls, timeout=300):
        return [copy.deepcopy(answers[url]) for url in urls]
    monkeypatch.setattr(serverModel, "asyncFetcher", fakeFetcher)
    redisModel.saveServerStatus(up.uuid, okStatus(clock[0]))
    emitted.clear()

    asyncio.run(serverModel.fetchServerInfoAsync(up, {
        "udpate_server": lambda server_id, data: seenAtPublish.append("update"),
        "udpate_server_usage": lambda server, data: seenAtPublish.append("usage"),
    }))

    events = healthEvents(emitted)
    assert len(events) == 1, "One update per refresh, not one per saved section"
    payload, room = events[0]
    assert room == f"user:{fleet.alice.id}"
    assert not any(issue["rule"] == "stale" for issue in payload["issues"])  # Evaluated on the new snapshot
    assert seenAtPublish == ["update", "usage"]


def test_acknowledging_publishes_health(client, auth_headers, fleet, emitted):
    down = fleet.servers["down"]
    issueID = f"unreachable:{down.id}"
    ack(client, auth_headers, fleet.alice, issueID, note="known")
    (payload, room), = healthEvents(emitted)
    assert room == f"user:{fleet.alice.id}"
    assert next(issue for issue in payload["issues"] if issue["id"] == issueID)["ack"]["note"] == "known"

    emitted.clear()
    client.delete(f"/health/ack/{issueID}", headers=auth_headers(fleet.alice))
    (payload, room), = healthEvents(emitted)
    assert next(issue for issue in payload["issues"] if issue["id"] == issueID)["ack"] is None


def test_deleting_a_server_publishes_no_issues_and_forgets_its_acknowledgements(client, auth_headers, db, fleet, emitted):
    from application.DBModels import HealthAck
    down = fleet.servers["down"]
    downID, fleetID = down.id, down.fleet_id
    ack(client, auth_headers, fleet.alice, f"unreachable:{downID}")
    emitted.clear()

    db.session.delete(down)
    db.session.commit()

    assert healthEvents(emitted) == [({"server_id": downID, "fleet_id": fleetID, "issues": []}, f"user:{fleet.alice.id}")]
    assert HealthAck.query.filter_by(server_id=downID).count() == 0


def test_publishing_never_breaks_a_refresh(monkeypatch, fleet, clock):
    import application.models.health as healthModel
    import application.models.servers as serverModel

    def broken(*args, **kwargs):
        raise RuntimeError("engine exploded")
    monkeypatch.setattr(healthModel, "evaluateServers", broken)
    result = serverModel.recordConnectionTest(fleet.servers["up"], okStatus(clock[0]))
    assert result["version"] == "3.0.0"


# --- Migration --------------------------------------------------------------------------------------------------------

def test_migration_creates_and_drops_the_acknowledgements_table(flask_cli):
    flask_cli.upgrade()
    tables = flask_cli.python(
        "import sqlite3, os; c = sqlite3.connect(os.environ['SQLALCHEMY_DATABASE_URI']);"
        "print([r[0] for r in c.execute(\"select name from sqlite_master where type='table'\")])")
    assert "health_acks" in tables.stdout
    downgraded = flask_cli.run("db", "downgrade", "f5b8d1c3a6e2")
    assert downgraded.returncode == 0, downgraded.stderr
    tables = flask_cli.python(
        "import sqlite3, os; c = sqlite3.connect(os.environ['SQLALCHEMY_DATABASE_URI']);"
        "print([r[0] for r in c.execute(\"select name from sqlite_master where type='table'\")])")
    assert "health_acks" not in tables.stdout
