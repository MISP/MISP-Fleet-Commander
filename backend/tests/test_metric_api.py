"""Reading the stored metrics (`/servers/metrics/<id>`) and the live benchmarks (`/servers/benchmarks/<id>`)"""
import time

import pytest

HOUR = 3600
DAY = 24 * HOUR
BASE = 1_790_000_000 - 1_790_000_000 % DAY  # A UTC midnight
SETTINGS = {"enabled": True, "interval": 600, "max_concurrency": 2}


@pytest.fixture(autouse=True)
def _app(app):
    """The models need the app first"""


@pytest.fixture()
def owned(db, make_user):
    """A server of Alice in a monitored fleet; Bob owns nothing"""
    from application.DBModels import Fleet, Server
    alice, bob = make_user("api-alice@test.local"), make_user("api-bob@test.local")
    fleet = Fleet(name="api-metrics", description="", user_id=alice.id, timestamp=1, is_monitored=True)
    db.session.add(fleet)
    db.session.commit()
    server = Server(name="api-misp", url="https://api.test", authkey="k" * 40, fleet_id=fleet.id, user_id=alice.id)
    db.session.add(server)
    db.session.commit()
    yield alice, bob, server
    if server in db.session:
        db.session.delete(server)
    db.session.delete(fleet)
    db.session.commit()


def add(db, server, tier, ts, values, samples=1, peaks=None):
    from application.DBModels import MetricSample
    db.session.add(MetricSample(server_id=server.id, tier=tier, ts=ts, values=values, samples=samples, peaks=peaks))
    db.session.commit()


# --- Request ----------------------------------------------------------------------------------------------------------

def test_request_defaults_and_validation():
    from application.models.metricCatalogue import CATALOGUE
    from application.models.metricSeries import SeriesRequestError, parseRequest
    assert parseRequest(None, None, None) == ("7d", "hour", [metric.key for metric in CATALOGUE])
    assert parseRequest("24h", None, "events, logins,events") == ("24h", "raw", ["events", "logins"])
    assert parseRequest("1y", None, None)[1] == "day"
    assert parseRequest("30d", "day", None)[1] == "day"  # Daily login bars over a month
    for args, message in ((("2w", None, None), "Unknown range"), (("7d", "minute", None), "Unknown tier"),
                          (("30d", "raw", None), "only covers 14 days"), (("1y", "hour", None), "only covers 90 days"),
                          (("7d", None, "events,nope"), "Unknown metric `nope`")):
        with pytest.raises(SeriesRequestError, match=message):
            parseRequest(*args)


def test_tier_limits_follow_the_retention(monkeypatch):
    import application.models.setting as settingModel
    from application.models.metricSeries import SeriesRequestError, parseRequest
    values = {"monitoring_raw_retention_days": 30, "monitoring_hour_retention_days": 365,
              "monitoring_day_retention_days": 0}
    original = settingModel.getRefreshValue
    monkeypatch.setattr(settingModel, "getRefreshValue", lambda name: values[name] if name in values else original(name))
    assert parseRequest("30d", "raw", None)[1] == "raw"
    assert parseRequest("1y", "hour", None)[1] == "hour"
    values.update({"monitoring_raw_retention_days": 2, "monitoring_hour_retention_days": 30})
    for args in (("7d", "raw", None), ("90d", "hour", None)):
        with pytest.raises(SeriesRequestError):
            parseRequest(*args)
    # The default tier of each range stays whole at the shortest retentions
    assert parseRequest("24h", None, None)[1] == "raw"
    assert parseRequest("30d", None, None)[1] == "hour"


def test_route_is_scoped_and_validated(client, auth_headers, owned):
    alice, bob, server = owned
    assert client.get(f"/servers/metrics/{server.id}").status_code == 401
    assert client.get(f"/servers/metrics/{server.id}", headers=auth_headers(bob)).status_code == 404
    assert client.get(f"/servers/benchmarks/{server.id}", headers=auth_headers(bob)).status_code == 404
    answer = client.get(f"/servers/metrics/{server.id}?range=2w", headers=auth_headers(alice))
    assert answer.status_code == 400 and "Unknown range" in answer.get_json()["message"]
    answer = client.get(f"/servers/metrics/{server.id}?range=24h&metrics=events", headers=auth_headers(alice))
    assert answer.status_code == 200
    body = answer.get_json()
    assert body["tier"] == "raw" and body["series"] == {"events": []} and body["latest"] is None
    assert body["metrics"] == {"events": {"label": "Events", "group": "content", "kind": "total", "unit": "count"}}


def test_the_answer_says_whether_the_collection_still_runs(client, auth_headers, owned, monkeypatch):
    import application.models.metrics as metrics
    alice, _, server = owned
    now = int(time.time())
    metrics.noteCollectorRun(now - 30)
    body = client.get(f"/servers/metrics/{server.id}?range=24h", headers=auth_headers(alice)).get_json()
    assert body["state"]["collector"] == {"last_run": now - 30, "stalled": False}
    metrics.noteCollectorRun(now - 3600)
    body = client.get(f"/servers/metrics/{server.id}?range=24h", headers=auth_headers(alice)).get_json()
    assert body["state"]["collector"] == {"last_run": now - 3600, "stalled": True}


# --- Series -----------------------------------------------------------------------------------------------------------

def test_raw_series(db, owned):
    from application.models.metricSeries import series
    server = owned[2]
    now = BASE + 20 * HOUR
    add(db, server, "raw", now - DAY - 60, {"events": 1})  # Before the range
    add(db, server, "raw", now - 3000, {"events": 2, "load_1": 0.5})
    add(db, server, "raw", now - 2400, {"events": 3, "load_1": 0.7, "logins": 2})
    answer = series(server, "24h", "raw", ["events", "load_1", "logins"], SETTINGS, now=now)
    assert answer["series"] == {"events": [[now - 3000, 2], [now - 2400, 3]],
                                "load_1": [[now - 3000, 0.5], [now - 2400, 0.7]], "logins": [[now - 2400, 2]]}
    assert answer["peaks"] == {} and answer["partial_since"] is None and answer["interval_s"] == 600
    assert (answer["from"], answer["to"]) == (now - DAY, now)
    assert answer["latest"] == {"ts": now - 2400, "values": {"events": 3, "load_1": 0.7, "logins": 2}}


def test_hour_series_runs_up_to_now(db, owned):
    """Stored hours, then the hours the roll-up has not written yet, from the raw rows after the last stored hour"""
    from application.models.metricSeries import series
    server = owned[2]
    now = BASE + 10 * HOUR + 1800
    add(db, server, "hour", BASE + 7 * HOUR, {"events": 5, "load_1": 1.0}, samples=6, peaks={"load_1": 2.0})
    add(db, server, "hour", BASE + 8 * HOUR, {"events": 6, "load_1": 3.0}, samples=6, peaks={"load_1": 4.0})
    add(db, server, "raw", BASE + 8 * HOUR + 100, {"events": 999, "load_1": 99.0})  # Already in its hour
    add(db, server, "raw", BASE + 9 * HOUR + 600, {"events": 7, "load_1": 2.0, "logins": 1})
    add(db, server, "raw", BASE + 9 * HOUR + 1200, {"events": 8, "load_1": 4.0, "logins": 2})
    add(db, server, "raw", BASE + 10 * HOUR + 300, {"events": 9, "load_1": 5.0, "logins": 3})
    answer = series(server, "7d", "hour", ["events", "load_1", "logins"], SETTINGS, now=now)
    hours = [BASE + h * HOUR for h in (7, 8, 9, 10)]
    assert answer["series"]["events"] == [[hours[0], 5], [hours[1], 6], [hours[2], 8], [hours[3], 9]]
    assert answer["series"]["load_1"] == [[hours[0], 1.0], [hours[1], 3.0], [hours[2], 3.0], [hours[3], 5.0]]
    assert answer["series"]["logins"] == [[hours[2], 3], [hours[3], 3]]
    assert answer["peaks"] == {"load_1": [[hours[0], 2.0], [hours[1], 4.0], [hours[2], 4.0], [hours[3], 5.0]]}
    assert answer["partial_since"] == hours[3] and answer["interval_s"] == HOUR
    assert answer["latest"]["ts"] == BASE + 10 * HOUR + 300


def test_day_series_runs_up_to_now(db, owned):
    """Stored days, then days built from hour rows and the raw rows of hours not rolled up yet"""
    from application.models.metricSeries import series
    server = owned[2]
    now = BASE + 2 * DAY + 10 * HOUR + 1800
    add(db, server, "day", BASE, {"events": 10, "logins": 4, "load_1": 1.0}, samples=144, peaks={"load_1": 3.0})
    add(db, server, "hour", BASE + DAY + 5 * HOUR, {"events": 11, "logins": 2, "load_1": 2.0}, samples=6,
        peaks={"load_1": 2.5})
    add(db, server, "hour", BASE + 2 * DAY + 3 * HOUR, {"logins": 1, "failed_logins": 1}, samples=0)  # Backfilled
    add(db, server, "hour", BASE + 2 * DAY + 8 * HOUR, {"events": 12, "load_1": 4.0}, samples=6,
        peaks={"load_1": 6.0})
    add(db, server, "raw", BASE + 2 * DAY + 8 * HOUR + 60, {"events": 999})  # Already in its hour
    add(db, server, "raw", BASE + 2 * DAY + 9 * HOUR + 60, {"events": 13, "logins": 5, "load_1": 1.0})
    answer = series(server, "90d", "day", ["events", "logins", "failed_logins", "load_1"], SETTINGS, now=now)
    days = [BASE, BASE + DAY, BASE + 2 * DAY]
    assert answer["series"]["events"] == [[days[0], 10], [days[1], 11], [days[2], 13]]
    assert answer["series"]["logins"] == [[days[0], 4], [days[1], 2], [days[2], 6]]
    assert answer["series"]["failed_logins"] == [[days[2], 1]]
    assert answer["series"]["load_1"] == [[days[0], 1.0], [days[1], 2.0], [days[2], round(25 / 7, 3)]]
    assert answer["peaks"]["load_1"] == [[days[0], 3.0], [days[1], 2.5], [days[2], 6.0]]
    assert "events" not in answer["peaks"]  # Only gauges have peaks
    assert answer["partial_since"] == days[2] and answer["interval_s"] == DAY


def test_collection_state(db, owned, monkeypatch):
    import application.models.metrics as metrics
    from application.models.metricSeries import series
    server = owned[2]
    answer = series(server, "24h", "raw", ["events"], SETTINGS)
    assert answer["state"] == {"enabled": True, "fleet_monitored": True, "has_authkey": True, "interval_s": 600,
                               "last_attempt": None, "last_success": None, "last_error": None}
    metrics.storeCollection(server.id, {"values": {}, "errors": ["Statistics: Server unreachable"], "logins": None},
                            now=1234)
    server.fleet.is_monitored = False
    db.session.commit()
    state = series(server, "24h", "raw", ["events"], dict(SETTINGS, enabled=False))["state"]
    assert state == {"enabled": False, "fleet_monitored": False, "has_authkey": True, "interval_s": 600,
                     "last_attempt": 1234, "last_success": None, "last_error": "Statistics: Server unreachable"}


# --- Benchmarks -------------------------------------------------------------------------------------------------------

def bench(key, value, unit):
    return {"scope": "endpoint", "field": "x", "date": "2026-11-18", "key": key, "text": key, "value": value,
            "unit": unit}


TOTALS = {
    "time": [bench("Shell::/default", 432074.6, "s"), bench("servers/serverSettings", 182.28, "s"),
             bench("servers/testConnection", 106.07, "s"), bench("Shell::Event/updateGalaxies", 90.5, "s"),
             bench("users/statistics", 12, "s"), bench("events/index", 11, "s"), bench("events/view", 3, "s"),
             bench("broken", "n/a", "s")],
    "sql_time": [bench("Shell::Event/updateGalaxies", 754, "ms"), bench("servers/testConnection", 540, "ms")],
    "memory": [bench("servers/testConnection", 1358, "MB"), bench("servers/serverSettings", 833, "MB")],
}
AVERAGES = {
    "time": [bench("servers/serverSettings", 4.239, "s"), bench("servers/testConnection", 0.5, "s")],
    "sql_time": [bench("servers/testConnection", 3, "ms")],
    "memory": [bench("servers/testConnection", 12, "MB")],
}


def test_top_endpoints():
    from application.models.benchmarks import topEndpoints
    time_ = topEndpoints("time", TOTALS["time"], AVERAGES["time"])
    assert time_["unit"] == "s"
    assert [entry["endpoint"] for entry in time_["top"]] == [
        "servers/serverSettings", "servers/testConnection", "Shell::Event/updateGalaxies", "users/statistics",
        "events/index"]  # The queue workers are left out; top 5
    assert time_["top"][0] == {"endpoint": "servers/serverSettings", "job": False, "total": 182.28, "average": 4.239}
    assert time_["top"][2]["job"] is True and time_["top"][2]["average"] is None
    sql = topEndpoints("sql_time", TOTALS["sql_time"], AVERAGES["sql_time"])
    assert sql["unit"] == "s" and sql["top"][0]["total"] == 0.754 and sql["top"][1]["average"] == 0.003
    memory = topEndpoints("memory", TOTALS["memory"], AVERAGES["memory"])
    assert memory == {"unit": "bytes", "top": [
        {"endpoint": "servers/testConnection", "job": False, "total": 1358 * 1024 ** 2, "average": 12 * 1024 ** 2},
        {"endpoint": "servers/serverSettings", "job": False, "total": 833 * 1024 ** 2, "average": None}]}
    assert topEndpoints("memory", [], []) == {"unit": "bytes", "top": []}


@pytest.fixture()
def fakeMispBenchmarks(monkeypatch):
    import application.models.benchmarks as benchmarks
    calls = []
    answers = {"mode": "data"}

    async def fetch(server, urls, timeout=None):
        calls.append(list(urls))
        result = []
        for url in urls:
            if answers["mode"] == "refused":
                result.append({"name": "Forbidden", "message": "Forbidden", "_status_code": 403})
                continue
            field = url.split("field:")[1].split("/")[0]
            rows = (AVERAGES if url.endswith("/average:1") else TOTALS)[field]
            result.append([] if answers["mode"] == "empty" else list(rows))
        return result
    monkeypatch.setattr(benchmarks, "asyncFetcher", fetch)
    return calls, answers


def test_benchmarks_are_fetched_and_cached(client, auth_headers, owned, fakeMispBenchmarks):
    from application import redisModel
    calls, answers = fakeMispBenchmarks
    alice, _, server = owned
    redisModel.redisClient.delete(f"server-benchmarks:{server.id}")
    body = client.get(f"/servers/benchmarks/{server.id}", headers=auth_headers(alice)).get_json()
    day = body["date"]
    assert calls[0] == [f"/benchmarks/index/scope:endpoint/field:{field}/days[]:{day}{suffix}"
                        for field in ("time", "sql_time", "memory") for suffix in ("", "/average:1")]
    assert body["cached"] is False and "note" not in body and "error" not in body
    assert body["fields"]["time"]["top"][0]["endpoint"] == "servers/serverSettings"
    assert body["fields"]["memory"]["unit"] == "bytes"

    again = client.get(f"/servers/benchmarks/{server.id}", headers=auth_headers(alice)).get_json()
    assert again["cached"] is True and len(calls) == 1 and again["fields"] == body["fields"]
    client.get(f"/servers/benchmarks/{server.id}?refresh=1", headers=auth_headers(alice))
    assert len(calls) == 2


def test_benchmarks_empty_refused_or_without_key(client, auth_headers, owned, fakeMispBenchmarks, db):
    from application import redisModel
    calls, answers = fakeMispBenchmarks
    alice, _, server = owned
    answers["mode"] = "empty"
    body = client.get(f"/servers/benchmarks/{server.id}?refresh=1", headers=auth_headers(alice)).get_json()
    assert body["fields"]["time"] == {"unit": "s", "top": []} and "benchmarking may be off" in body["note"]

    answers["mode"] = "refused"
    redisModel.redisClient.delete(f"server-benchmarks:{server.id}")
    body = client.get(f"/servers/benchmarks/{server.id}", headers=auth_headers(alice)).get_json()
    assert body["error"] == "MISP refused to show its benchmarks: the API key needs site admin rights"
    assert redisModel.redisClient.get(f"server-benchmarks:{server.id}") is None  # Errors are not cached

    server.authkey = None
    db.session.commit()
    calls.clear()
    body = client.get(f"/servers/benchmarks/{server.id}", headers=auth_headers(alice)).get_json()
    assert body["error"] == "No API key configured" and calls == []


def test_deleting_a_server_forgets_its_benchmarks(db, owned):
    from application import redisModel
    server = owned[2]
    redisModel.redisClient.set(f"server-benchmarks:{server.id}", "{}")
    serverId = server.id
    db.session.delete(server)
    db.session.commit()
    assert redisModel.redisClient.get(f"server-benchmarks:{serverId}") is None
