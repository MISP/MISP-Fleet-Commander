"""Sync link health: parsing MISP's connection test, classifying each link, and the health sent with the network"""
import copy
import json
from pathlib import Path

import pytest

SNAPSHOT = json.loads((Path(__file__).parent / "fixtures" / "snapshot_misp_3.0.0.json").read_text())
LATEST = "v3.0.1"
TESTED_AT = 1_900_000_000

# What MISP's /servers/testConnection answers for a healthy link
OK = {"status": 1, "version": "3.0.1", "local_version": "3.0.1", "mismatch": False, "newer": False, "post": 1,
      "uuid": "00000000-0000-4000-8000-000000000009"}
SYNC_USER = {"User": "sync@remote.test", "Role name": "Sync user", "Sync flag": "Yes"}
PLAIN_USER = {"User": "user@remote.test", "Role name": "User", "Sync flag": "No"}


@pytest.fixture(autouse=True)
def _app(app):
    """The parsers and the health code import the application"""


def parse(test):
    from application.models.servers import parseMISPConnectionOutput
    return parseMISPConnectionOutput({**test, "timestamp": TESTED_AT})


def parseUser(user):
    from application.models.servers import parseMISPUserConnectionOutput
    return parseMISPUserConnectionOutput(user)


def link(test=OK, user=SYNC_USER, **flags):
    """A connection as the full refresh stores it. Push and pull are on unless given"""
    return {"Server": {"id": "9", "name": "Remote", "push": True, "pull": True, **flags},
            "connectionTest": None if test is None else parse(test),
            "connectionUser": parseUser(user)}


def lazy(**fields):
    """`link()` built when the test runs: the parser needs the app, which does not exist yet at collection time"""
    return lambda: link(**fields)


def classify(link, latest=LATEST):
    from application.health.links import classify_link
    return classify_link(link, latest)


def codes(health):
    return [(reason["level"], reason["code"]) for reason in health["reasons"]]


# --- Parsing the connection test --------------------------------------------------------------------------------------

def test_parser_keeps_misps_raw_values():
    parsed = parse({**OK, "mismatch": "hotfix", "newer": "local"})
    assert parsed["timestamp"] == TESTED_AT
    assert parsed["status"] == {"message": "Remote outdated, notify admin!", "color": "success", "authorized": True,
                                "code": 1}
    assert parsed["compatibility"] == {"message": "Compatible", "color": "warning", "mismatch": "hotfix",
                                       "newer": "local"}
    assert parsed["post"] == {"result": "Received sent package", "color": "success", "success": True, "code": 1}
    assert "authorized" not in parsed and "test_error" not in parsed


@pytest.mark.parametrize("code, color, message, authorized", [
    (2, "danger", "Server unreachable", False), (3, "danger", "Unexpected error", False),
    (4, "danger", "Authentication failed", False), (5, "danger", "Password change required", False),
    (6, "danger", "Terms not accepted", False), (7, "warning", "Remote user is not a sync user", True),
    (8, "warning", "Syncing sightings only", True), (99, "danger", "Unkown response status", False),
])
def test_parser_status_codes(code, color, message, authorized):
    parsed = parse({"status": code})
    assert parsed["status"] == {"message": message, "color": color, "authorized": authorized, "code": code}
    assert "test_error" not in parsed


@pytest.mark.parametrize("answer, error", [
    ({"error": "Timeout Exception (5s)"}, "Timeout Exception (5s)"),
    ({"_status_code": 403, "name": "Forbidden", "message": "You do not have permission"}, "You do not have permission"),
    ({"_status_code": 500}, "HTTP 500"),
])
def test_parser_flags_tests_that_did_not_run(answer, error):
    parsed = parse(answer)
    assert parsed["test_error"] == error
    assert parsed["status"]["message"] == error and parsed["status"]["code"] is None


# --- Classification ---------------------------------------------------------------------------------------------------

def test_healthy_link():
    assert classify(link()) == {"level": "ok", "reasons": [], "disabled": False, "push": True, "pull": True,
                                "tested_at": TESTED_AT}


@pytest.mark.parametrize("name, connection, latest, level, expected", [
    # No test result
    ("never tested", lazy(test=None), LATEST, "unknown", [("unknown", "not_tested")]),
    ("request timed out", lazy(test={"error": "Timeout Exception (5s)"}), LATEST, "unknown", [("unknown", "test_failed")]),
    ("not allowed to test", lazy(test={"_status_code": 403, "message": "Forbidden"}), LATEST, "unknown",
     [("unknown", "test_failed")]),
    # The connection itself
    ("unreachable", lazy(test={"status": 2}, user={}), LATEST, "broken", [("broken", "status")]),
    ("auth failed", lazy(test={"status": 4}, user={}), LATEST, "broken", [("broken", "status")]),
    ("terms", lazy(test={"status": 6}, user={}), LATEST, "broken", [("broken", "status")]),
    ("unknown status", lazy(test={"status": 99}, user={}), LATEST, "broken", [("broken", "status")]),
    ("sightings only", lazy(test={"status": 8}), LATEST, "degraded", [("degraded", "sightings_only")]),
    # Remote user
    ("not a sync user, push", lazy(test={"status": 7}, user=PLAIN_USER), LATEST, "broken",
     [("broken", "no_sync_permission")]),
    ("not a sync user, pull only", lazy(test={"status": 7}, user=PLAIN_USER, push=False), LATEST, "degraded",
     [("degraded", "no_sync_permission")]),
    ("not a sync user, nothing pushed or pulled", lazy(test={"status": 7}, user={}, push=False, pull=False,
                                                      push_sightings=True), LATEST, "ok", []),
    ("user without sync flag, push", lazy(user=PLAIN_USER), LATEST, "broken", [("broken", "no_sync_permission")]),
    ("remote user not readable", lazy(user={"message": "Timeout"}), LATEST, "ok", []),
    # Versions
    ("hotfix mismatch", lazy(test={**OK, "version": "3.0.0", "mismatch": "hotfix", "newer": "local"}), None,
     "degraded", [("degraded", "version_mismatch")]),
    ("compatible major mismatch (MISP 3.0 and 2.5)",
     lazy(test={**OK, "version": "2.5.51", "local_version": "3.0.0", "mismatch": "major_compatible", "newer": "local"}),
     "v2.5.50", "degraded", [("degraded", "version_mismatch")]),
    ("pull only, push on", lazy(test={**OK, "version": "2.5.0", "mismatch": "minor", "newer": "local"}), None,
     "broken", [("broken", "pull_only")]),
    ("pull only, push off", lazy(test={**OK, "version": "2.5.0", "mismatch": "minor", "newer": "local"}, push=False),
     None, "degraded", [("degraded", "pull_only")]),
    ("major mismatch", lazy(test={**OK, "version": "2.5.0", "mismatch": "major", "newer": "local"}), None,
     "broken", [("broken", "incompatible")]),
    ("remote newer", lazy(test={**OK, "version": "3.1.0", "mismatch": "minor", "newer": "remote"}), None,
     "broken", [("broken", "incompatible")]),
    ("proposals", lazy(test={**OK, "mismatch": "proposal", "newer": False}), None, "degraded",
     [("degraded", "compatibility")]),
    ("remote outdated", lazy(test={**OK, "version": "3.0.0", "local_version": "3.0.0"}), LATEST, "degraded",
     [("degraded", "remote_outdated")]),
    ("remote newer than the latest release", lazy(test={**OK, "version": "3.1.0", "local_version": "3.1.0"}),
     LATEST, "ok", []),
    ("latest release unknown", lazy(test={**OK, "version": "2.4.0", "local_version": "2.4.0"}), None, "ok", []),
    # Push test
    ("push test failed", lazy(test={**OK, "post": 8}), LATEST, "broken", [("broken", "push_test_failed")]),
    ("push test failed, push off", lazy(test={**OK, "post": 9}, push=False), LATEST, "ok", []),
    ("remote too old for the push test", lazy(test={**OK, "post": 3}), LATEST, "ok", []),
    ("push test not run", lazy(test={**OK, "post": False}), LATEST, "ok", []),
    # Several reasons: the worst wins
    ("outdated and refusing pushes", lazy(test={**OK, "version": "3.0.0", "local_version": "3.0.0", "post": 10}),
     LATEST, "broken", [("degraded", "remote_outdated"), ("broken", "push_test_failed")]),
])
def test_classification(name, connection, latest, level, expected):
    health = classify(connection(), latest)
    assert (health["level"], sorted(codes(health))) == (level, sorted(expected)), name
    assert all(reason["message"] for reason in health["reasons"])


def test_reasons_explain_what_to_do():
    assert classify(link(test={"status": 4}, user={}))["reasons"][0]["message"] == "Authentication failed"
    assert classify(link(user=PLAIN_USER))["reasons"][0]["message"] == \
        "Remote user user@remote.test lacks the sync permission: the remote refuses pushes"
    assert classify(link(test={"status": 7}, user={}))["reasons"][0]["message"] == \
        "The remote user lacks the sync permission: the remote refuses pushes"
    assert classify(link(test={**OK, "post": 8}))["reasons"][0]["message"] == "Push test failed: Could not POST message"
    assert classify(link(test={"error": "Timeout Exception (5s)"}))["reasons"][0]["message"] == \
        "The test did not complete: Timeout Exception (5s)"
    assert classify(link(test={**OK, "version": "3.0.1", "local_version": "3.0.0", "mismatch": "hotfix",
                               "newer": "remote"}))["reasons"][0]["message"] == \
        "MISP versions differ (local 3.0.0, remote 3.0.1): the local instance should be updated"


@pytest.mark.parametrize("flags, disabled", [
    ({"push": False, "pull": False}, True),
    ({"push": "0", "pull": "0", "caching_enabled": "0"}, True),
    ({"push": False, "pull": False, "push_sightings": True}, False),
    ({"push": False, "pull": False, "caching_enabled": True}, False),
    ({"push": False, "pull": False, "pull_galaxy_clusters": "1"}, False),
    ({"push": False, "pull": True}, False),
])
def test_unused_links(flags, disabled):
    health = classify(link(**flags))
    assert health["disabled"] is disabled
    assert health["level"] == "ok"  # Being unused does not change the level


def test_snapshots_taken_before_the_raw_values_were_kept():
    """Older snapshots have no status code, test error or post code: they are recovered from the messages"""
    def legacy(status, post=None, **test):
        return {"Server": {"id": "1", "push": True, "pull": True},
                "connectionTest": {"status": status, "post": post or {"result": "", "success": False}, **test},
                "connectionUser": {"email": "", "sync_flag": False}}
    assert codes(classify(legacy({"color": "danger", "message": "Authentication failed"}))) == [("broken", "status")]
    assert codes(classify(legacy({"color": "danger", "message": "Timeout Exception (5s)"}))) == [("unknown", "test_failed")]
    assert codes(classify(legacy({"color": "warning", "message": "Remote user is not a sync user"}))) == \
        [("broken", "no_sync_permission")]
    assert codes(classify(legacy({"color": "success", "message": "OK"}, post={"result": "Invalid body"},
                                 remoteVersion="3.0.1"))) == [("broken", "push_test_failed")]
    assert classify(legacy({"color": "danger", "message": "OK"}))["tested_at"] is None


def test_fixture_links_classify_without_errors():
    from application.health.links import LEVELS
    for connection in SNAPSHOT["query_result"]["connectedServers"]:
        assert classify(connection)["level"] in LEVELS


# --- Network and connection endpoints ---------------------------------------------------------------------------------

@pytest.fixture()
def networkFleet(db, make_user, monkeypatch):
    import application.health.versions as versions
    from application import redisModel
    from application.DBModels import Fleet, Server
    monkeypatch.setattr(versions, "latest_release", lambda: LATEST)
    user = make_user("links-owner@test.local")
    fleet = Fleet(name="Links", description="", user_id=user.id, timestamp=1)
    db.session.add(fleet)
    db.session.commit()
    server = Server(name="hub", url="https://hub.test", authkey="k" * 40, fleet_id=fleet.id, user_id=user.id)
    db.session.add(server)
    db.session.commit()
    snapshot = copy.deepcopy(SNAPSHOT)
    snapshot.pop("_fixture", None)  # Describes the fixture, not part of a snapshot
    snapshot["query_result"]["connectedServers"] = [
        {**link(), "Server": {**SNAPSHOT["query_result"]["connectedServers"][0]["Server"], "id": "1", "push": True}},
        {**link(test={"status": 4}, user={}),
         "Server": {**SNAPSHOT["query_result"]["connectedServers"][0]["Server"], "id": "2", "pull": True}},
    ]
    redisModel.saveServerInfo(server.uuid, snapshot)
    yield user, fleet, server
    db.session.delete(server)
    db.session.commit()
    db.session.delete(fleet)
    db.session.commit()


def test_network_links_carry_their_health(client, auth_headers, networkFleet):
    user, fleet, server = networkFleet
    response = client.get(f"/servers/network/{fleet.id}", headers=auth_headers(user))
    assert response.status_code == 200
    links = {link["destination"]["Server"]["id"]: link for link in response.get_json()}
    assert {remote: (link["health"]["level"], link["tested_at"]) for remote, link in links.items()} == {
        "1": ("ok", TESTED_AT), "2": ("broken", TESTED_AT)}
    assert links["2"]["health"]["reasons"] == [{"level": "broken", "code": "status", "message": "Authentication failed"}]


def test_single_connection_carries_its_health(client, auth_headers, networkFleet):
    user, fleet, server = networkFleet
    response = client.get(f"/servers/getConnection/{server.id}/2", headers=auth_headers(user))
    assert response.status_code == 200
    assert response.get_json()["health"]["level"] == "broken"
