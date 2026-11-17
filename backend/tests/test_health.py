"""Health-rules engine: rules on a real (anonymised) MISP 3.0.0 snapshot and variations of it, parity with the fleet
table's status colours, issue IDs, ordering and first-seen tracking"""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "snapshot_misp_3.0.0.json"
SNAPSHOT = json.loads(FIXTURE.read_text())
NOW = SNAPSHOT["timestamp"] + 60
LATEST = "v2.5.51"


@pytest.fixture(autouse=True)
def _app(app):
    """Rules and first-seen tracking use the app's (fake) Redis"""


def server(id=1, authkey="k" * 40, fleet_id=7):
    return SimpleNamespace(id=id, uuid=f"uuid-{id}", fleet_id=fleet_id, authkey=authkey)


def snapshot(**serverSettings):
    data = copy.deepcopy(SNAPSHOT)
    data["query_result"]["serverSettings"].update(serverSettings)
    return data


def okStatus(**fields):
    return {"version": "3.0.0", "_latency": 0.27, "_status_code": 200, "timestamp": NOW - 30, **fields}


def ctx(**fields):
    from application.health import Context
    return Context(**{"now": NOW, "latest_release": LATEST, **fields})


def evaluate(snapshotData=None, status=None, srv=None, **ctxFields):
    from application.health import ServerState, evaluate_state
    return evaluate_state(ServerState(srv or server(), SNAPSHOT if snapshotData is None else snapshotData,
                                      okStatus() if status is None else status), ctx(**ctxFields))


def byRule(issues):
    found = {}
    for issue in issues:
        found.setdefault(issue.rule, []).append(issue)
    return found


def setFinalSetting(data, name, value):
    for entry in data["query_result"]["serverSettings"]["finalSettings"]:
        if entry["setting"] == name:
            entry["value"] = value
            return data
    raise KeyError(name)


# --- Versions ---------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("v2.5.1", (2, 5, 1)), ("2.5.1", (2, 5, 1)), ("2.5", (2, 5, 0)), ("v3.0.0-rc1", (3, 0, 0)),
    ("2.4.199 (a1b2c3)", (2, 4, 199)), ("garbage", None), ("", None), (None, None), ("v2", None),
])
def test_parse_version(text, expected):
    from application.health.versions import parse_version
    assert parse_version(text) == expected


@pytest.mark.parametrize("current, latest, expected", [
    ((2, 5, 51), (2, 5, 51), None), ((3, 0, 0), (2, 5, 51), None), ((2, 5, 52), (2, 5, 51), None),
    ((2, 5, 40), (2, 5, 51), "patch"), ((2, 4, 199), (2, 5, 1), "minor"), ((1, 9, 9), (2, 5, 1), "major"),
    (None, (2, 5, 1), None), ((2, 5, 1), None, None),
])
def test_how_far_behind(current, latest, expected):
    from application.health.versions import how_far_behind
    assert how_far_behind(current, latest) == expected


def test_latest_release_is_cached(monkeypatch):
    from application.health import versions
    from application import redisModel
    redisModel.redisClient.delete(versions.KEY_LATEST_RELEASE)
    calls = []
    monkeypatch.setattr(versions, "fetch_latest_release", lambda: calls.append(1) or "v2.5.51")
    assert versions.latest_release() == "v2.5.51"
    assert versions.latest_release() == "v2.5.51"
    assert len(calls) == 1
    assert 0 < redisModel.redisClient.ttl(versions.KEY_LATEST_RELEASE) <= versions.LATEST_RELEASE_TTL


def test_failed_latest_release_lookup_is_remembered(monkeypatch):
    from application.health import versions
    from application import redisModel
    redisModel.redisClient.delete(versions.KEY_LATEST_RELEASE)
    calls = []
    monkeypatch.setattr(versions, "fetch_latest_release", lambda: calls.append(1) or None)
    assert versions.latest_release() is None
    assert versions.latest_release() is None
    assert len(calls) == 1
    assert redisModel.redisClient.ttl(versions.KEY_LATEST_RELEASE) <= versions.LATEST_RELEASE_FAILURE_TTL
    redisModel.redisClient.delete(versions.KEY_LATEST_RELEASE)


@pytest.mark.parametrize("github, current, expected", [
    ("v2.5.51", "3.0.0", True),  # Newer than GitHub's latest release: used to be shown as outdated
    ("v2.5.51", "2.5.51", True), ("v2.5.51", "2.5.50", False), ("?", "?", None), ("v2.5.51", "?", None),
    ("v2.5.51", "not-a-version", None),
])
def test_up_to_date_plugin(github, current, expected):
    from application.plugins.UpToDate import UpToDate
    assert UpToDate.isUpToDate(github, current) is expected
    assert UpToDate.tokenizeMISPVersion("garbage") == {"major": "?", "minor": "?", "patch": "?"}  # Used to raise


# --- The real snapshot ------------------------------------------------------------------------------------------------

def test_real_snapshot():
    """MISP 3.0.0 with healthy workers, Cortex disabled, the AI modules unreachable and several broken sync links"""
    issues = byRule(evaluate())
    assert set(issues) == {"modules", "sync_link"}
    assert [(i.subject, i.severity) for i in issues["modules"]] == [("AI", "info")]  # Cortex: not enabled ≠ broken
    # 1: pushes sightings, test fails · 2, 4: unused, test fails · 3: pull, unreachable · 5: push, test fails ·
    # 6: pull, OK (no issue) · 7: push + pull, unreachable · 9: unused, OK
    assert {i.subject: i.severity for i in issues["sync_link"]} == {
        "1": "critical", "2": "info", "3": "critical", "4": "info", "5": "critical", "7": "critical", "9": "info"}
    assert all(i.category == "sync" and i.action == {"kind": "open_tab", "target": "connections"}
               for i in issues["sync_link"])


def test_issue_ids_are_stable():
    issues = evaluate(srv=server(id=42))
    assert {i.id for i in issues if i.rule == "modules"} == {"modules:42:AI"}
    assert all(i.id.startswith(f"{i.rule}:42") and i.server_id == 42 and i.fleet_id == 7 for i in issues)
    assert [i.id for i in evaluate(srv=server(id=42))] == [i.id for i in issues]


def test_issues_are_serializable():
    for issue in evaluate():
        data = issue.to_dict()
        json.dumps(data)
        assert set(data) == {"id", "rule", "severity", "category", "server_id", "fleet_id", "title", "detail",
                             "subject", "evidence", "action", "first_seen"}


def test_issue_dict_is_a_copy_with_every_field():
    """`to_dict` replaced `dataclasses.asdict` (too slow for thousands of issues): same result, nested values copied"""
    import dataclasses
    from application.health.engine import Issue

    issue = Issue(id="r:1:s", rule="r", severity="info", category="config", server_id=1, fleet_id=2, title="t",
                  detail="d", subject="s", evidence={"expected": {"name": "x"}, "values": [1, {"a": 2}], "pair": (1, 2)},
                  action={"kind": "open_baseline", "rule_id": 3}, first_seen=10)
    data = issue.to_dict()
    assert data == dataclasses.asdict(issue)
    assert set(data) == {f.name for f in dataclasses.fields(Issue)}
    data["evidence"]["expected"]["name"] = "changed"
    data["evidence"]["values"][1]["a"] = 0
    data["action"]["kind"] = "changed"
    assert issue.evidence == {"expected": {"name": "x"}, "values": [1, {"a": 2}], "pair": (1, 2)}
    assert issue.action == {"kind": "open_baseline", "rule_id": 3}


# --- Availability -----------------------------------------------------------------------------------------------------

def test_no_api_key():
    issues = evaluate(srv=server(authkey=None), status={"error": "No API key configured", "timestamp": NOW})
    assert [(i.rule, i.title) for i in issues] == [("auth_failed", "No API key configured")]


@pytest.mark.parametrize("status_code", [401, 403])
def test_authentication_failure(status_code):
    issues = evaluate(status={"error": "Authentication error", "_status_code": status_code, "timestamp": NOW})
    assert [(i.rule, i.severity) for i in issues] == [("auth_failed", "critical")]


def test_unreachable_server_reports_one_root_cause():
    """Rules reading the (old) snapshot are skipped: only availability and freshness are reported"""
    issues = evaluate(status={"error": "Connection Error: Cannot connect to host", "timestamp": NOW})
    assert [(i.rule, i.severity) for i in issues] == [("unreachable", "critical")]
    assert "Cannot connect" in issues[0].detail
    assert issues[0].action == {"kind": "test_connection"}

    stale = evaluate(status={"error": "Timeout", "timestamp": NOW}, snapshotData={"timestamp": NOW - 5 * 3600})
    assert {i.rule for i in stale} == {"unreachable", "stale"}


def test_answer_without_version_is_unreachable():
    issues = evaluate(status={"text": "<html>maintenance</html>", "_status_code": 200, "timestamp": NOW})
    assert [i.rule for i in issues] == ["unreachable"]


@pytest.mark.parametrize("latency, expected", [(0.27, []), (1.99, []), (2.0, ["slow"]), (12.5, ["slow"])])
def test_slow(latency, expected):
    issues = evaluate(status=okStatus(_latency=latency))
    assert [i.rule for i in issues if i.rule == "slow"] == expected


# --- Freshness --------------------------------------------------------------------------------------------------------

def test_never_refreshed_or_tested():
    issues = [i for i in evaluate(snapshotData={}, status={}) if i.rule == "stale"]
    assert [(i.subject, i.title) for i in issues] == [("connection", "Connection never tested"),
                                                     ("snapshot", "Never refreshed")]


def test_stale_thresholds_follow_the_intervals():
    data = copy.deepcopy(SNAPSHOT)
    data["timestamp"] = NOW - 61 * 60
    assert {i.subject for i in evaluate(data) if i.rule == "stale"} == {"snapshot"}  # > 2 × 30 min
    assert not [i for i in evaluate(data, full_refresh_interval=3600) if i.rule == "stale"]
    oldTest = okStatus(timestamp=NOW - 11 * 60)
    assert {i.subject for i in evaluate(status=oldTest) if i.rule == "stale"} == {"connection"}  # > 2 × 5 min


# --- Snapshot content -------------------------------------------------------------------------------------------------

def test_fetch_errors():
    data = copy.deepcopy(SNAPSHOT)
    data["query_result"]["serverSettings"] = {"error": "Timeout Exception (300s)"}
    data["query_result"]["serverUser"] = {"name": "Authentication failed.", "message": "Authentication failed.",
                                          "_status_code": 403}
    issues = byRule(evaluate(data))
    assert {(i.subject, i.detail) for i in issues["fetch_error"]} == {
        ("serverSettings", "Timeout Exception (300s)"), ("serverUser", "Authentication failed.")}
    # Rules reading the missing diagnostics have nothing to say
    assert not set(issues) & {"workers_none", "workers_dead", "jobs_backlog", "modules", "background_jobs_disabled"}


@pytest.mark.parametrize("current, latest, severity", [
    ("2.5.51", LATEST, None), ("3.0.0", LATEST, None), ("2.5.40", LATEST, "warning"),
    ("2.4.199", LATEST, "critical"), ("1.0.0", LATEST, "critical"), ("garbage", LATEST, None),
])
def test_outdated(current, latest, severity):
    issues = [i for i in evaluate(status=okStatus(version=current)) if i.rule == "outdated"]
    assert [i.severity for i in issues] == ([severity] if severity else [])


def test_outdated_falls_back_to_the_release_misp_reports():
    """Without GitHub, the snapshot's `version.newest` (from MISP itself) is used"""
    data = snapshot(version={"current": "v2.5.10", "newest": "v2.5.51", "upToDate": "older"})
    issues = [i for i in evaluate(data, status=okStatus(version="2.5.10"), latest_release=None) if i.rule == "outdated"]
    assert [(i.severity, i.evidence["latest"]) for i in issues] == [("warning", "2.5.51")]


def test_background_jobs_disabled():
    data = setFinalSetting(copy.deepcopy(SNAPSHOT), "MISP.background_jobs", False)
    issues = byRule(evaluate(data))
    assert [i.severity for i in issues["background_jobs_disabled"]] == ["critical"]
    assert not set(issues) & {"workers_none", "workers_dead", "jobs_backlog"}


def test_no_worker_at_all():
    issues = byRule(evaluate(snapshot(workers={})))
    assert [(i.subject, i.severity) for i in issues["workers_none"]] == [(None, "critical")]


def uiQueueVariant(queue, total, dead, jobCount, warning=10, danger=100):
    """The fleet table's colour for a queue (workersStatus.vue: getVariantFromAliveAndJobCount / getVariantFromAlive)"""
    if total == 0:
        return "danger"
    if dead == 0:
        if queue == "update":
            return ""
        return "" if jobCount <= warning else ("warning" if jobCount <= danger else "danger")
    return "danger" if dead == total else "warning"


def queueWith(total, dead, jobCount):
    return {"ok": dead == 0, "jobCount": jobCount,
            "workers": [{"pid": i, "user": "www-data", "alive": i >= dead, "correct_user": True, "ok": i >= dead}
                        for i in range(total)]}


@pytest.mark.parametrize("queue", ["cache", "default", "prio", "update", "email"])
@pytest.mark.parametrize("total, dead", [(0, 0), (1, 0), (5, 0), (5, 1), (5, 5), (1, 1)])
@pytest.mark.parametrize("jobCount", [0, 10, 11, 100, 101, 5000])
def test_worker_parity_with_the_fleet_table(queue, total, dead, jobCount):
    workers = copy.deepcopy(SNAPSHOT["query_result"]["serverSettings"]["workers"])
    workers[queue] = queueWith(total, dead, jobCount)
    issues = [i for i in evaluate(snapshot(workers=workers)) if i.category == "workers"]
    assert all(i.subject == queue for i in issues)
    severities = {i.severity for i in issues}
    worst = "danger" if "critical" in severities else ("warning" if "warning" in severities else "")
    assert worst == uiQueueVariant(queue, total, dead, jobCount)
    assert len(issues) <= 1  # One finding per queue: missing, dead or backlog


def test_backlog_thresholds_come_from_the_context():
    workers = copy.deepcopy(SNAPSHOT["query_result"]["serverSettings"]["workers"])
    workers["default"]["jobCount"] = 30
    data = snapshot(workers=workers)
    assert [i.severity for i in evaluate(data) if i.rule == "jobs_backlog"] == ["warning"]
    assert [i.severity for i in evaluate(data, worker_danger_threshold=20) if i.rule == "jobs_backlog"] == ["critical"]
    assert [i for i in evaluate(data, worker_warning_threshold=50) if i.rule == "jobs_backlog"] == []


@pytest.mark.parametrize("status, expected", [(0, None), (1, None), (2, "Python library not installed correctly"),
                                              (3, "ZMQ script not running"), (7, "Unknown status code 7")])
def test_zmq(status, expected):
    """Unlike the fleet table, ZeroMQ being disabled (1) is not an issue"""
    issues = [i for i in evaluate(snapshot(zmqStatus=status)) if i.rule == "zmq"]
    assert [i.detail for i in issues] == ([expected] if expected else [])


@pytest.mark.parametrize("status, failing", [("not configured (so not tested)", False), ("OK", False), ("", False),
                                             ("Getting URL via proxy failed", True)])
def test_proxy(status, failing):
    assert bool([i for i in evaluate(snapshot(proxyStatus=status)) if i.rule == "proxy"]) is failing


def test_modules():
    issues = [i for i in evaluate(snapshot(moduleStatus={"Enrichment": 0, "Import": "0", "Export": 2, "Cortex": 1,
                                                         "AI": "curl error 7"})) if i.rule == "modules"]
    assert {(i.subject, i.detail, i.severity) for i in issues} == {("Export", "No modules found", "info"),
                                                                  ("AI", "curl error 7", "info")}


def test_sync_links():
    """One issue per link that is not OK, severity from its level (see test_links.py for the classification)"""
    from application.models.servers import parseMISPConnectionOutput

    def link(remote_id, test, push=True, pull=True):
        return {"Server": {"id": remote_id, "name": f"Remote {remote_id}", "url": "https://r.example.org",
                           "push": push, "pull": pull},
                "connectionTest": None if test is None else parseMISPConnectionOutput({**test, "timestamp": NOW - 5}),
                "connectionUser": {"email": "sync@r.example.org", "sync_flag": True}}
    ok = {"status": 1, "version": "2.5.51", "local_version": "3.0.0", "mismatch": False, "newer": False, "post": 1}
    data = copy.deepcopy(SNAPSHOT)
    data["query_result"]["connectedServers"] = [
        link("1", ok), link("2", {**ok, "mismatch": "hotfix", "newer": "local"}), link("3", {"status": 4}),
        link("4", None), link("5", {"status": 2}, push=False, pull=False), link("6", ok, push=False, pull=False),
    ]
    issues = [i for i in evaluate(data) if i.rule == "sync_link"]
    assert [(i.id, i.severity, i.title, i.detail) for i in issues] == [
        ("sync_link:1:3", "critical", "Broken sync link to Remote 3", "Authentication failed"),
        ("sync_link:1:2", "warning", "Degraded sync link to Remote 2", "MISP versions differ (local 3.0.0, remote 2.5.51): the remote instance should be updated"),
        ("sync_link:1:4", "info", "Untested sync link to Remote 4", "The link has not been tested yet"),
        ("sync_link:1:5", "info", "Unused sync link to Remote 5", "Push, pull and caching are all off; Server unreachable"),
        ("sync_link:1:6", "info", "Unused sync link to Remote 6", "Push, pull and caching are all off"),
    ]
    broken = issues[0].evidence
    assert broken["level"] == "broken" and broken["tested_at"] == NOW - 5 and broken["push"] and broken["pull"]
    assert broken["reasons"] == [{"level": "broken", "code": "status", "message": "Authentication failed"}]
    assert (broken["remote_id"], broken["remote_name"]) == ("3", "Remote 3")


def test_outdated_remote_falls_back_to_the_version_misp_reports():
    """Without GitHub, a remote behind the `newest` version the local MISP reports is degraded"""
    from application.models.servers import parseMISPConnectionOutput
    data = copy.deepcopy(SNAPSHOT)
    data["query_result"]["serverSettings"]["version"]["newest"] = "v3.0.1"
    data["query_result"]["connectedServers"] = [{
        "Server": {"id": "1", "name": "R", "push": False, "pull": True},
        "connectionTest": parseMISPConnectionOutput({"status": 1, "version": "3.0.0", "local_version": "3.0.0",
                                                     "mismatch": False, "newer": False, "post": False}),
        "connectionUser": {"email": "sync@r", "sync_flag": True}}]
    assert [(i.severity, i.detail) for i in evaluate(data, latest_release=None) if i.rule == "sync_link"] == [
        ("warning", "The remote runs 3.0.0, the latest release is 3.0.1")]
    assert [i for i in evaluate(data) if i.rule == "sync_link"] == []  # GitHub's v2.5.51 is older


# --- Engine -----------------------------------------------------------------------------------------------------------

def test_sorting():
    from application.health import Issue, sort_issues, worst_severity

    def make(id, severity, first_seen):
        return Issue(id=id, rule="r", severity=severity, category="config", server_id=1, fleet_id=1, title=id,
                     first_seen=first_seen)
    issues = [make("info", "info", 1), make("w-new", "warning", 20), make("c", "critical", 30), make("w-old", "warning", 10)]
    assert [i.id for i in sort_issues(issues)] == ["c", "w-old", "w-new", "info"]
    assert worst_severity(issues) == "critical"
    assert worst_severity([]) is None


def test_rules_can_be_added_and_a_broken_rule_does_not_hide_others(monkeypatch):
    from application.health import Finding, engine, rule
    engine.ensure_rules_loaded()
    monkeypatch.setattr(engine, "RULES", list(engine.RULES))

    @rule("custom_check", "config")
    def custom(state, ctx):
        yield Finding("warning", "Custom", subject="x")

    @rule("broken_check", "config")
    def broken(state, ctx):
        raise RuntimeError("boom")

    issues = evaluate()
    assert "custom_check:1:x" in {i.id for i in issues}
    assert "modules" in {i.rule for i in issues}
    with pytest.raises(ValueError):
        rule("custom_check", "config")(custom)
    with pytest.raises(ValueError):
        rule("other", "no-such-category")


def test_first_seen_tracking():
    from application.health import evaluate_server
    from application import redisModel
    srv = server(id=9001)
    redisModel.redisClient.delete("health-first-seen:9001")
    broken = okStatus(_latency=3.0)

    first = {i.id: i.first_seen for i in evaluate_server(srv, ctx(), snapshot=SNAPSHOT, status=broken)}
    assert first["slow:9001"] == NOW
    later = ctx(now=NOW + 600)
    second = {i.id: i.first_seen for i in evaluate_server(srv, later, snapshot=SNAPSHOT, status=broken)}
    assert {id: second[id] for id in first} == first  # Still the time they first appeared
    assert second["stale:9001:connection"] == NOW + 600  # Appeared since: the connection test got old

    # It clears, then comes back: a new "since"
    cleared = {i.id for i in evaluate_server(srv, ctx(now=NOW + 700), snapshot=SNAPSHOT, status=okStatus())}
    assert "slow:9001" not in cleared
    assert "slow:9001" not in redisModel.redisClient.hgetall("health-first-seen:9001")
    again = {i.id: i.first_seen for i in evaluate_server(srv, ctx(now=NOW + 800), snapshot=SNAPSHOT, status=broken)}
    assert again["slow:9001"] == NOW + 800


def test_evaluate_server_reads_redis():
    from application.health import evaluate_server
    from application import redisModel
    srv = server(id=9002)
    redisModel.saveServerInfo(srv.uuid, SNAPSHOT)
    redisModel.saveServerStatus(srv.uuid, {"error": "Server unreachable", "timestamp": NOW})
    assert [i.rule for i in evaluate_server(srv, ctx(), track_first_seen=False)] == ["unreachable"]


def test_context_for_user(db, make_user):
    from application.DBModels import UserSettings
    from application.health import Context
    user = make_user("health-ctx@test.local")
    for name, value in (("UI.server_index.worker_warning_threshold", "25"),
                        ("UI.server_index.worker_danger_threshold", "not a number")):
        setting = UserSettings(user_id=user.id, name=name)
        setting.value = value
        db.session.add(setting)
    db.session.commit()

    context = Context.for_user(user, now=123, latest_release="v2.5.51")

    assert (context.now, context.worker_warning_threshold, context.worker_danger_threshold) == (123, 25, 100)
    assert (context.connection_test_interval, context.full_refresh_interval) == (300, 1800)
    assert context.latest_release == "v2.5.51"
    for setting in UserSettings.query.filter_by(user_id=user.id).all():
        db.session.delete(setting)
    db.session.commit()


def test_deleting_a_server_forgets_its_first_seen(db, make_user):
    from application.DBModels import Fleet, Server
    from application import redisModel
    user = make_user("health-delete@test.local")
    fleet = Fleet(name="Health", description="", user_id=user.id, timestamp=1)
    db.session.add(fleet)
    db.session.commit()
    srv = Server(name="h", url="https://h.test", authkey="k" * 40, fleet_id=fleet.id, user_id=user.id)
    db.session.add(srv)
    db.session.commit()
    redisModel.syncHealthFirstSeen(srv.id, ["slow:x"], NOW)
    key = f"health-first-seen:{srv.id}"
    assert redisModel.redisClient.exists(key)

    db.session.delete(srv)
    db.session.delete(fleet)
    db.session.commit()

    assert not redisModel.redisClient.exists(key)


# --- Pending registrations --------------------------------------------------------------------------------------------

MISP_REGISTRATIONS = [{"Inbox": {
    "id": str(i), "uuid": f"00000000-0000-4000-8000-00000000000{i}", "title": "User registration", "type": "registration",
    "ip": "192.0.2.10", "user_agent": "Mozilla/5.0", "user_agent_sha256": "ab" * 32, "comment": "", "deleted": False,
    "timestamp": "1793970000", "store_as_file": False,
    "data": {"email": f"new{i}@example.org", "org_name": f"Org {i}", "message": "Please let me in"},
}} for i in range(1, 6)]


def test_registrations_are_summarized_without_personal_details():
    from application.models.servers import summarizeRegistrations
    summary = summarizeRegistrations(MISP_REGISTRATIONS[:1])
    assert summary == [{"id": "1", "uuid": "00000000-0000-4000-8000-000000000001", "timestamp": "1793970000",
                        "email": "new1@example.org", "org_name": "Org 1"}]
    assert summarizeRegistrations([]) == []
    assert summarizeRegistrations({"error": "Authentication error", "_status_code": 403})["error"]
    assert summarizeRegistrations("<html>") == {"error": "Unexpected answer"}


def withRegistrations(registrations):
    data = copy.deepcopy(SNAPSHOT)
    data["query_result"]["userRegistrations"] = registrations
    return data


@pytest.mark.parametrize("count, title, detail", [
    (1, "1 pending account request", "new1@example.org (Org 1)"),
    (5, "5 pending account requests",
     "new1@example.org (Org 1), new2@example.org (Org 2), new3@example.org (Org 3) and 2 more"),
])
def test_pending_registrations(count, title, detail):
    from application.models.servers import summarizeRegistrations
    issues = [i for i in evaluate(withRegistrations(summarizeRegistrations(MISP_REGISTRATIONS[:count])))
              if i.rule == "pending_registrations"]
    assert [(i.id, i.severity, i.category, i.title, i.detail) for i in issues] == [
        ("pending_registrations:1", "info", "users", title, detail)]
    assert issues[0].evidence["count"] == count
    assert issues[0].action == {"kind": "open_misp", "path": "/users/registrations"}


@pytest.mark.parametrize("registrations", [
    [],                                                          # Nothing pending
    {"error": "Insufficent permission", "_status_code": 405},    # API user cannot see registrations: not an issue
    None,                                                        # Snapshot taken before registrations were collected
])
def test_no_pending_registration_issue(registrations):
    issues = evaluate(withRegistrations(registrations) if registrations is not None else SNAPSHOT)
    assert not [i for i in issues if i.rule in ("pending_registrations", "fetch_error")]


def test_full_refresh_collects_registrations(monkeypatch):
    import asyncio
    import application.models.servers as serverModel
    from application import redisModel
    srv = server(id=9003)
    answers = {
        "/servers/serverSettings/diagnostics/light:1": SNAPSHOT["query_result"]["serverSettings"],
        "/users/view/me": {"User": {"id": "1"}},
        "/servers/index": [],
        "/users/registrations": MISP_REGISTRATIONS[:2],
        "/users/statistics": {"stats": {}},
    }

    async def fakeFetcher(server, urls, timeout=300):
        return [copy.deepcopy(answers[url]) for url in urls]
    monkeypatch.setattr(serverModel, "asyncFetcher", fakeFetcher)
    monkeypatch.setattr(redisModel, "setServerWatchedTimestamp", lambda uuid: None)

    asyncio.run(serverModel.fetchServerInfoAsync(srv, {}))

    stored = redisModel.getServerInfo(srv.uuid)["query_result"]["userRegistrations"]
    assert [r["email"] for r in stored] == ["new1@example.org", "new2@example.org"]
    assert "192.0.2.10" not in json.dumps(stored) and "Mozilla" not in json.dumps(stored)
    redisModel.deleteServerData(srv.uuid, srv.id)
