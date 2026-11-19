"""Collecting usage metrics: requests, partial failures, login counting and backfill, samples and state, scheduling"""
import copy
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "metrics_misp_3.0.0.json").read_text())
HOUR = 3600
WIDGETS = {"MispSystemResourceWidget": "system_widget", "MispAdminResourceWidget": "admin_widget",
           "APIActivityWidget": "api_activity_widget"}
GETS = {"/users/statistics": "statistics", "/users/registrations": "registrations",
        "/servers/serverSettings/diagnostics/light:1": "diagnostics"}


@pytest.fixture(autouse=True)
def _app(app):
    """The collector imports the models, which need the app (and its fake Redis) first"""


def created(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def logRow(logId, action, ts):
    return {"Log": {"id": str(logId), "action": action, "created": created(ts), "model": "User",
                    "title": "User (1): user@misp.test", "email": "user@misp.test", "ip": "192.0.2.1"}}


class FakeMisp:
    """Answers the metric requests from the MISP 3.0.0 fixture. `overrides` replaces an answer by source name
    (statistics, system_widget, …); `logs(created)` answers the log searches"""

    def __init__(self, overrides=None, logs=None):
        self.answers = copy.deepcopy(FIXTURE)
        self.answers.update(overrides or {})
        self.logs = logs or (lambda created: {"data": [], "_status_code": 200})
        self.calls = []

    def get(self, server, url, data={}, nocache=False, timeout=None, **kwargs):
        self.calls.append(("GET", url))
        return copy.deepcopy(self.answers[GETS[url]])

    def post(self, server, url, data={}, timeout=None, **kwargs):
        if url == "/admin/logs/index":
            assert data["model"] == "User" and data["action"] == ["login", "login_fail"] and data["limit"] == 5000
            self.calls.append(("LOGS", data["created"]))
            return self.logs(data["created"])
        self.calls.append(("POST", data["widget"]))
        return copy.deepcopy(self.answers[WIDGETS[data["widget"]]])

    def install(self, monkeypatch):
        import application.models.metrics as metrics
        monkeypatch.setattr(metrics, "mispGetRequest", self.get)
        monkeypatch.setattr(metrics, "mispPostRequest", self.post)
        return self


def target():
    from application.models.metrics import Target
    return Target(1, "misp", "https://misp.test", "k" * 40, False)


def backfilledState(cursor=None, read_at=None):
    from application.models.metrics import LoginState
    return LoginState(cursor=cursor, backfilled=True, read_at=read_at)


# --- Requests ---------------------------------------------------------------------------------------------------------

def test_every_source_is_read(monkeypatch):
    from application.models.metrics import fetchServerMetrics
    misp = FakeMisp().install(monkeypatch)
    result = fetchServerMetrics(target(), backfilledState(read_at=int(time.time()) - 600), 600)
    assert result["errors"] == []
    values = result["values"]
    assert values["events"] == 4291 and values["pending_registrations"] == 1 and values["queue_default"] == 0
    assert values["load_5"] == 4.869140625 and values["db_size_bytes"] == int(round(8893.8 * 1024 ** 2))
    assert values["api_requests_24h"] == 1998
    assert values["redis_memory_bytes"] == 42894624  # From the diagnostics, exact, rather than the widget's MB
    assert result["logins"]["counts"] == {"logins": 0, "failed_logins": 0}
    assert [call[0] for call in misp.calls] == ["GET", "GET", "GET", "POST", "POST", "POST", "LOGS"]


def test_a_failing_source_leaves_its_keys_out(monkeypatch):
    from application.models.metrics import fetchServerMetrics
    FakeMisp({"system_widget": {"error": "Request timed out"},
              "registrations": {"name": "Not Found", "message": "Not Found", "_status_code": 404},
              "api_activity_widget": {"data": [{"title": "x", "html": "garbage"}], "_status_code": 200}}
             ).install(monkeypatch)
    result = fetchServerMetrics(target(), backfilledState(), 600)
    assert "load_1" not in result["values"] and "pending_registrations" not in result["values"]
    assert "api_requests_24h" not in result["values"]
    assert result["values"]["events"] == 4291 and result["values"]["db_size_bytes"] > 0
    assert result["errors"] == ["Registrations: HTTP 404: Not Found", "System widget: Request timed out",
                                "API activity widget: No request count in the API activity widget"]


def test_an_unreachable_server_is_asked_once(monkeypatch):
    from application.models.metrics import fetchServerMetrics
    misp = FakeMisp({"statistics": {"error": "Server unreachable"}}).install(monkeypatch)
    result = fetchServerMetrics(target(), backfilledState(), 600)
    assert misp.calls == [("GET", "/users/statistics")]
    assert result == {"values": {}, "errors": ["Statistics: Server unreachable"], "logins": None}


def test_a_server_refusing_the_key_is_not_asked_its_logs(monkeypatch):
    from application.models.metrics import fetchServerMetrics
    refused = {"error": "Authentication error", "_status_code": 403}
    misp = FakeMisp({name: refused for name in ("statistics", "registrations", "diagnostics", "system_widget",
                                                "admin_widget", "api_activity_widget")}).install(monkeypatch)
    result = fetchServerMetrics(target(), backfilledState(), 600)
    assert result["values"] == {} and result["logins"] is None and len(result["errors"]) == 6
    assert not any(call[0] == "LOGS" for call in misp.calls)


# --- Logins -----------------------------------------------------------------------------------------------------------

def test_logins_above_the_cursor_are_counted(monkeypatch):
    from application.models.metrics import readLogins
    now = int(time.time())
    misp = FakeMisp(logs=lambda created: {"data": [logRow(99, "login", now - 60), logRow(101, "login", now - 50),
                                                   logRow(102, "login_fail", now - 40),
                                                   logRow(103, "login", now - 30)]}).install(monkeypatch)
    result = readLogins(target(), backfilledState(cursor=100, read_at=now - 600), 600, now)
    assert result == {"counts": {"logins": 2, "failed_logins": 1}, "cursor": 103, "error": None}
    assert misp.calls == [("LOGS", "20m")]  # 10 minutes since the last read, plus the margin


def test_login_window(monkeypatch):
    from application.models.metrics import loginWindowMinutes
    now = 1_000_000
    assert loginWindowMinutes(backfilledState(read_at=now - 600), 600, now) == 20
    assert loginWindowMinutes(backfilledState(read_at=now - 601), 600, now) == 21
    assert loginWindowMinutes(backfilledState(), 300, now) == 15  # Never read: the interval
    assert loginWindowMinutes(backfilledState(read_at=now - 7 * 86400), 600, now) == 1440


def test_without_a_cursor_every_entry_counts(monkeypatch):
    from application.models.metrics import readLogins
    now = int(time.time())
    FakeMisp(logs=lambda created: {"data": [logRow(5, "login", now - 60)]}).install(monkeypatch)
    result = readLogins(target(), backfilledState(), 600, now)
    assert result["counts"] == {"logins": 1, "failed_logins": 0} and result["cursor"] == 5


def test_a_full_log_page_is_a_floor(monkeypatch):
    from application.models.metrics import readLogins
    now = int(time.time())
    FakeMisp(logs=lambda created: {"data": [logRow(i, "login", now) for i in range(1, 5001)]}).install(monkeypatch)
    result = readLogins(target(), backfilledState(cursor=0, read_at=now - 600), 600, now)
    assert result["counts"]["logins"] == 5000 and "some were not counted" in result["error"]


def test_unreadable_logs(monkeypatch):
    from application.models.metrics import readLogins
    FakeMisp(logs=lambda created: {"error": "Insufficent permission", "_status_code": 405}).install(monkeypatch)
    result = readLogins(target(), backfilledState(cursor=7), 600, int(time.time()))
    assert result == {"counts": None, "error": "Logins: MISP refused to list its logs: the API key needs admin rights"}
    FakeMisp(logs=lambda created: {"name": "Oops", "_status_code": 200}).install(monkeypatch)
    assert readLogins(target(), backfilledState(cursor=7), 600, int(time.time()))["counts"] is None


def test_backfill_steps_down_and_buckets_by_hour(monkeypatch):
    """90 days hit the 5000-entry limit: 30 days are read. Ended hours become hour counts, zero included, the current
    hour goes into the first sample"""
    from application.models.metrics import LoginState, readLogins
    now = int(time.time())
    hourStart = now - now % HOUR
    recent = [logRow(10, "login", hourStart - 2 * HOUR + 5), logRow(11, "login", hourStart - 2 * HOUR + 50),
              logRow(12, "login_fail", hourStart - HOUR + 1), logRow(13, "login", hourStart),
              logRow(14, "login_fail", hourStart + 4 * HOUR)]  # MISP ahead of UTC: counted now
    answers = {"90d": {"data": [logRow(i, "login", now) for i in range(5000)]}, "30d": {"data": recent}}
    misp = FakeMisp(logs=lambda created: answers[created]).install(monkeypatch)
    result = readLogins(target(), LoginState(), 600, now)
    assert misp.calls == [("LOGS", "90d"), ("LOGS", "30d")]
    assert {bucket: counts for bucket, counts in result["hours"].items() if any(counts.values())} == {
        hourStart - 2 * HOUR: {"logins": 2, "failed_logins": 0},
        hourStart - HOUR: {"logins": 0, "failed_logins": 1},
    }
    # Every hour of the 30 days read in full has its row: no login there is known, not missing
    assert len(result["hours"]) == 30 * 24 - 1
    assert result["hours"][hourStart - 3 * HOUR] == {"logins": 0, "failed_logins": 0}
    assert min(result["hours"]) > now - 30 * 24 * HOUR and max(result["hours"]) == hourStart - HOUR
    assert result["counts"] == {"logins": 1, "failed_logins": 1}
    assert result["cursor"] == 14 and result["backfilled"] and result["error"] is None


def test_backfill_with_too_many_entries_keeps_the_last_week(monkeypatch):
    from application.models.metrics import LoginState, readLogins
    now = int(time.time())
    misp = FakeMisp(logs=lambda created: {"data": [logRow(i, "login", now - 2 * HOUR) for i in range(5000)]}
                    ).install(monkeypatch)
    result = readLogins(target(), LoginState(), 600, now)
    assert [call[1] for call in misp.calls] == ["90d", "30d", "14d", "7d"]
    assert sum(hour["logins"] for hour in result["hours"].values()) == 5000
    assert "past 7 days" in result["error"]


def test_a_failed_backfill_is_not_retried(monkeypatch):
    from application.models.metrics import LoginState, readLogins
    FakeMisp(logs=lambda created: {"error": "Request timed out"}).install(monkeypatch)
    result = readLogins(target(), LoginState(), 600, int(time.time()))
    assert result == {"counts": None, "backfilled": True, "error": "Logins: Request timed out"}


# --- Storage ----------------------------------------------------------------------------------------------------------

@pytest.fixture()
def fleets(db, make_user):
    """A monitored fleet with two servers (one without API key) and an unmonitored one, of two users"""
    from application.DBModels import Fleet, Server
    alice, bob = make_user("metrics-alice@test.local"), make_user("metrics-bob@test.local")
    created = {}
    for name, user, monitored in (("monitored", alice, True), ("unmonitored", alice, False), ("bob", bob, True)):
        fleet = Fleet(name=f"metrics-{name}", description="", user_id=user.id, timestamp=1, is_monitored=monitored)
        db.session.add(fleet)
        db.session.commit()
        created[name] = fleet
    servers = {}
    for name, fleet, authkey in (("m1", "monitored", "a" * 40), ("m-nokey", "monitored", None),
                                 ("u1", "unmonitored", "b" * 40), ("b1", "bob", "c" * 40)):
        server = Server(name=f"metrics-{name}", url=f"https://{name}.test", authkey=authkey,
                        fleet_id=created[fleet].id, user_id=created[fleet].user_id)
        db.session.add(server)
        db.session.commit()
        servers[name] = server
    yield created, servers
    for server in servers.values():
        if server in db.session:
            db.session.delete(server)
    for fleet in created.values():
        db.session.delete(fleet)
    db.session.commit()


def samples(server_id, tier=None):
    from application.DBModels import MetricSample
    query = MetricSample.query.filter_by(server_id=server_id)
    if tier is not None:
        query = query.filter_by(tier=tier)
    return query.order_by(MetricSample.ts).all()


def test_first_collection_stores_the_sample_and_the_backfill(fleets):
    from application.models.metrics import storeCollection
    server = fleets[1]["m1"]
    now = int(time.time())
    hourStart = now - now % HOUR
    result = {"values": {"events": 10, "load_1": 0.5}, "errors": [],
              "logins": {"counts": {"logins": 1, "failed_logins": 0}, "cursor": 40, "backfilled": True, "error": None,
                         "hours": {hourStart - HOUR: {"logins": 3, "failed_logins": 2}}}}
    state = storeCollection(server.id, result, now)
    raw, = samples(server.id, "raw")
    assert (raw.ts, raw.values, raw.samples) == (now, {"events": 10, "load_1": 0.5, "logins": 1, "failed_logins": 0}, 1)
    hour, = samples(server.id, "hour")
    assert (hour.ts, hour.values, hour.samples) == (hourStart - HOUR, {"logins": 3, "failed_logins": 2}, 0)
    assert (state.login_cursor, state.logins_backfilled, state.logins_read_at) == (40, True, now)
    assert (state.logins_total, state.failed_logins_total) == (4, 2)
    assert (state.last_attempt, state.last_success, state.last_error) == (now, now, None)

    # Hours that already have a row are merged into, the others are added
    storeCollection(server.id, {"values": {"events": 11}, "errors": [], "logins": {
        "counts": {"logins": 0, "failed_logins": 0}, "cursor": 41, "error": None,
        "hours": {hourStart - HOUR: {"logins": 4, "failed_logins": 2},
                  hourStart - 2 * HOUR: {"logins": 0, "failed_logins": 0}}}}, now + 1)
    assert [(row.ts, row.values) for row in samples(server.id, "hour")] == [
        (hourStart - 2 * HOUR, {"logins": 0, "failed_logins": 0}),
        (hourStart - HOUR, {"logins": 4, "failed_logins": 2}),
    ]


def test_failures_are_recorded(fleets):
    from application.models.metrics import storeCollection
    server = fleets[1]["m1"]
    now = int(time.time())
    storeCollection(server.id, {"values": {"events": 1}, "errors": [], "logins": {"counts": {"logins": 0, "failed_logins": 0}, "cursor": 3, "error": None}}, now - 600)
    state = storeCollection(server.id, {"values": {}, "errors": ["Statistics: Server unreachable"], "logins": None}, now)
    assert len(samples(server.id)) == 1
    assert (state.last_attempt, state.last_success) == (now, now - 600)
    assert state.last_error == "Statistics: Server unreachable" and state.login_cursor == 3
    # Partly failed: the sample is stored and the failures are kept
    state = storeCollection(server.id, {"values": {"events": 2}, "errors": ["System widget: Request timed out"],
                                        "logins": {"counts": None, "error": "Logins: Request timed out"}}, now + 600)
    assert state.last_success == now + 600 and state.login_cursor == 3 and state.logins_read_at == now - 600
    assert state.last_error == "System widget: Request timed out; Logins: Request timed out"
    assert samples(server.id)[-1].values == {"events": 2}  # Logins not read: missing, not 0


def test_due_servers(fleets):
    from application.models import metrics
    from application.models.fleets import indexMonitored
    created, servers = fleets
    candidates = metrics.monitoredServers(indexMonitored())
    ours = {servers["m1"].id, servers["b1"].id}
    assert ours <= {server.id for server in candidates}
    assert servers["m-nokey"].id not in {server.id for server in candidates}
    assert servers["u1"].id not in {server.id for server in candidates}
    now = int(time.time())
    metrics.storeCollection(servers["m1"].id, {"values": {"events": 1}, "errors": [], "logins": None}, now - 120)
    due = {server.id for server in metrics.serversDueForCollection(candidates, 600, now)}
    assert servers["b1"].id in due and servers["m1"].id not in due
    due = {server.id for server in metrics.serversDueForCollection(candidates, 600, now + 460)}
    assert servers["m1"].id in due  # 30 s of slack


def test_deleting_a_server_deletes_its_metrics(db, fleets):
    from application.DBModels import MetricState
    from application.models.metrics import storeCollection
    server = fleets[1]["m1"]
    storeCollection(server.id, {"values": {"events": 1}, "errors": [], "logins": None})
    serverId = server.id
    db.session.delete(server)
    db.session.commit()
    assert samples(serverId) == [] and db.session.get(MetricState, serverId) is None


# --- Task -------------------------------------------------------------------------------------------------------------

@pytest.fixture()
def emitted(monkeypatch):
    import application.workers.tasks as tasks
    events = []
    monkeypatch.setattr(tasks.socketioEmitter.socketio, "emit",
                        lambda event, data=None, **kw: events.append((event, data, kw.get("to"))))
    return events


@pytest.fixture()
def monitoring(monkeypatch):
    import application.models.metrics as metrics
    config = {"enabled": True, "interval": 600, "max_concurrency": 2}
    monkeypatch.setattr(metrics, "monitoringSettings", lambda: dict(config))
    return config


def test_the_task_collects_due_servers_of_monitored_fleets(monkeypatch, fleets, emitted, monitoring):
    import application.workers.tasks as tasks
    from application import redisModel
    created, servers = fleets
    FakeMisp().install(monkeypatch)
    tasks.collectMetrics.call_local()
    for name in ("m1", "b1"):
        raw, = samples(servers[name].id, "raw")
        assert raw.values["events"] == 4291 and raw.values["logins"] == 0
    assert samples(servers["u1"].id) == [] and samples(servers["m-nokey"].id) == []
    updates = {data["fleet_id"]: (data, room) for event, data, room in emitted if event == "FLEET_UPDATE_TIMESTAMPS"}
    data, room = updates[created["monitored"].id]
    assert room == f"user:{created['monitored'].user_id}"
    assert data["monitored_timestamp"] == redisModel.getFleetMonitoredTimestamp(created["monitored"].id)
    assert updates[created["bob"].id][1] == f"user:{created['bob'].user_id}"
    assert created["unmonitored"].id not in updates

    # Not due again right away
    tasks.collectMetrics.call_local()
    assert len(samples(servers["m1"].id, "raw")) == 1


def test_a_server_failing_does_not_stop_the_others(monkeypatch, fleets, monitoring):
    import application.models.metrics as metrics
    import application.workers.tasks as tasks
    servers = fleets[1]
    FakeMisp().install(monkeypatch)
    original = metrics.fetchServerMetrics
    brokenId = servers["m1"].id  # Threads have no app context: models cannot be read there

    def broken(target, logins, interval):
        if target.id == brokenId:
            raise RuntimeError("parser bug")
        return original(target, logins, interval)
    monkeypatch.setattr(metrics, "fetchServerMetrics", broken)
    tasks.collectMetrics.call_local()
    from application.DBModels import MetricState, db
    assert db.session.get(MetricState, servers["m1"].id).last_error == "Collection failed: parser bug"
    assert len(samples(servers["b1"].id, "raw")) == 1


def test_the_task_does_nothing_when_monitoring_is_off(monkeypatch, fleets, monitoring):
    import application.workers.tasks as tasks
    misp = FakeMisp().install(monkeypatch)
    monitoring["enabled"] = False
    assert tasks.collectMetrics.call_local() is None
    assert misp.calls == []


def test_monitoring_settings(monkeypatch):
    import application.models.metrics as metrics
    import application.models.setting as settingModel
    assert settingModel.get("monitoring_enabled")["disabled"] is False
    assert settingModel.get("monitoring_enabled")["error"] is False
    assert settingModel.validate("monitoring_interval", 30) == 30
    for value in (0, 1441):
        with pytest.raises(settingModel.SettingError):
            settingModel.validate("monitoring_interval", value)
    values = {"monitoring_enabled": True, "monitoring_interval": 15, "health_max_concurrency": 4}
    monkeypatch.setattr(settingModel, "getRefreshValue", lambda name: values[name])
    monkeypatch.setattr(settingModel, "getValue", lambda name: values[name])
    assert metrics.monitoringSettings() == {"enabled": True, "interval": 900, "max_concurrency": 4}


# --- Migration --------------------------------------------------------------------------------------------------------

def test_migration_creates_and_drops_the_metric_tables(flask_cli):
    listTables = ("import sqlite3, os; c = sqlite3.connect(os.environ['SQLALCHEMY_DATABASE_URI']);"
                  "print([r[0] for r in c.execute(\"select name from sqlite_master where type='table'\")])")
    flask_cli.upgrade()
    tables = flask_cli.python(listTables).stdout
    assert "metric_samples" in tables and "metric_states" in tables
    downgraded = flask_cli.run("db", "downgrade", "b81c4f2e9a07")
    assert downgraded.returncode == 0, downgraded.stderr
    tables = flask_cli.python(listTables).stdout
    assert "metric_samples" not in tables and "metric_states" not in tables
