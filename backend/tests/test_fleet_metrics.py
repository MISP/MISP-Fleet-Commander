"""Usage metrics of a fleet (`/fleets/metrics/<id>`): sums over its servers and each server's figures"""
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
def fleet(db, make_user):
    """Alice's monitored fleet of three servers (b, a, c by id; a, b, c by name); Bob owns nothing"""
    from application.DBModels import Fleet, Server
    alice, bob = make_user("fleet-alice@test.local"), make_user("fleet-bob@test.local")
    theFleet = Fleet(name="fleet-metrics", description="", user_id=alice.id, timestamp=1, is_monitored=True)
    db.session.add(theFleet)
    db.session.commit()
    servers = {}
    for name in ("b", "a", "c"):
        servers[name] = Server(name=f"{name}-misp", url=f"https://{name}.test", authkey="k" * 40,
                               fleet_id=theFleet.id, user_id=alice.id)
        db.session.add(servers[name])
    db.session.commit()
    yield alice, bob, theFleet, servers
    db.session.rollback()
    db.session.delete(db.session.get(Fleet, theFleet.id))  # And its servers
    db.session.commit()


def add(db, server, tier, ts, values, samples=1, peaks=None):
    from application.DBModels import MetricSample
    db.session.add(MetricSample(server_id=server.id, tier=tier, ts=ts, values=values, samples=samples, peaks=peaks))
    db.session.commit()


def series(theFleet, rangeName, now, keys=None, settings=SETTINGS):
    from application.models import fleetMetrics
    from application.models.metricCatalogue import CATALOGUE
    _, tier, _ = fleetMetrics.parseRequest(rangeName, None)
    return fleetMetrics.fleetSeries(theFleet, rangeName, tier, keys or [metric.key for metric in CATALOGUE],
                                    settings, now=now)


def test_request():
    from application.models.fleetMetrics import parseRequest
    from application.models.metricSeries import SeriesRequestError
    assert [parseRequest(name, None)[1] for name in ("24h", "7d", "30d", "90d", "1y")] == \
        ["hour", "hour", "hour", "day", "day"]
    assert parseRequest(None, "logins") == ("7d", "hour", ["logins"])
    for args in (("2w", None), ("7d", "nope")):
        with pytest.raises(SeriesRequestError):
            parseRequest(*args)


def test_route_is_scoped_and_validated(client, auth_headers, fleet):
    alice, bob, theFleet, _ = fleet
    assert client.get(f"/fleets/metrics/{theFleet.id}").status_code == 401
    assert client.get(f"/fleets/metrics/{theFleet.id}", headers=auth_headers(bob)).status_code == 404
    response = client.get(f"/fleets/metrics/{theFleet.id}?range=2w", headers=auth_headers(alice))
    assert response.status_code == 400 and "Unknown range" in response.json["message"]
    answer = client.get(f"/fleets/metrics/{theFleet.id}?range=24h&metrics=events,load_1",
                        headers=auth_headers(alice)).json
    assert answer["tier"] == "hour" and answer["interval_s"] == HOUR
    assert answer["totals"] == {"events": []}  # The load doesn't add up across servers
    assert [server["name"] for server in answer["servers"]] == ["a-misp", "b-misp", "c-misp"]
    assert answer["state"]["servers"] == 3 and answer["state"]["fleet_monitored"] is True
    assert answer["metrics"]["events"]["summed"] is True and answer["metrics"]["load_1"]["summed"] is False
    # Whether the collection still runs
    import application.models.metrics as metrics
    now = int(time.time())
    metrics.noteCollectorRun(now - 3600)
    answer = client.get(f"/fleets/metrics/{theFleet.id}?range=24h", headers=auth_headers(alice)).json
    assert answer["state"]["collector"] == {"last_run": now - 3600, "stalled": True}


def test_levels_carry_forward_and_deltas_add_up(db, fleet):
    _, _, theFleet, servers = fleet
    a, b, c = servers["a"], servers["b"], servers["c"]
    now = BASE + 5 * DAY + 10 * HOUR
    h = [BASE + 5 * DAY + n * HOUR for n in range(4)]
    for ts, events, logins in zip(h[:3], (10, 11, 12), (2, 0, 1)):
        add(db, a, "hour", ts, {"events": events, "logins": logins, "db_size_bytes": 1000, "load_1": 1.5})
    # b misses the second hour: its events stay in the sum, its logins don't
    add(db, b, "hour", h[0], {"events": 100, "logins": 3, "db_size_bytes": 5000, "orgs": 7})
    add(db, b, "hour", h[2], {"events": 102, "db_size_bytes": 5100, "orgs": 7})
    # c starts in the fourth hour: the fleet grew
    add(db, c, "hour", h[3], {"events": 50, "failed_logins": 4})
    answer = series(theFleet, "7d", now)
    totals = answer["totals"]
    assert totals["events"] == [[h[0], 110], [h[1], 111], [h[2], 114], [h[3], 164]]
    assert totals["logins"] == [[h[0], 5], [h[1], 0], [h[2], 1]]
    assert totals["failed_logins"] == [[h[3], 4]]
    assert totals["db_size_bytes"] == [[h[0], 6000], [h[1], 6000], [h[2], 6100], [h[3], 6100]]
    assert "orgs" not in totals and "load_1" not in totals
    assert totals["attributes"] == []
    assert answer["reporting"] == [[h[0], 2], [h[1], 1], [h[2], 2], [h[3], 1]]
    assert answer["partial_since"] is None


def test_per_server_figures(db, fleet):
    _, _, theFleet, servers = fleet
    a = servers["a"]
    now = BASE + 5 * DAY + 10 * HOUR + 20 * 60
    h = [BASE + 5 * DAY + n * HOUR for n in range(3)]
    add(db, a, "hour", h[0], {"events": 10, "logins": 2, "load_1": 1.0, "db_size_bytes": 1000}, samples=6,
        peaks={"load_1": 4.0, "db_size_bytes": 1000})
    add(db, a, "hour", h[2], {"events": 15, "logins": 3, "failed_logins": 1, "load_1": 2.0, "db_size_bytes": 1400},
        samples=6, peaks={"load_1": 2.5, "db_size_bytes": 1500})
    add(db, a, "raw", now - 300, {"events": 16, "load_1": 0.5, "orgs": 3})
    answer = series(theFleet, "7d", now)
    byName = {server["name"]: server for server in answer["servers"]}
    figures = byName["a-misp"]
    assert figures["sums"] == {"logins": 5, "failed_logins": 1}
    assert figures["change"] == {"events": 6, "db_size_bytes": 400}  # Up to the pending hour's raw sample
    assert figures["peaks"] == {"load_1": 4.0}  # Load, memory and disk only
    assert figures["since"] == h[0]
    assert figures["latest"] == {"ts": now - 300, "values": {"events": 16, "load_1": 0.5, "orgs": 3}}
    assert figures["state"]["last_attempt"] is None and figures["state"]["has_authkey"] is True
    assert answer["latest_ts"] == now - 300
    assert answer["partial_since"] == now - now % HOUR
    assert byName["b-misp"] == {**byName["b-misp"], "latest": None, "sums": {}, "change": {}, "peaks": {},
                                "since": None}


def test_buckets_not_rolled_up_yet_are_summed_on_the_fly(db, fleet):
    _, _, theFleet, servers = fleet
    a, b = servers["a"], servers["b"]
    today = BASE + 10 * DAY
    now = today + 5 * HOUR + 20 * 60
    add(db, a, "day", today - DAY, {"events": 10, "logins": 1})
    add(db, a, "hour", today + HOUR, {"events": 12, "logins": 2})  # Rolled up hour of today
    add(db, a, "raw", today + 5 * HOUR + 600, {"events": 13, "logins": 4})  # Hour still running
    add(db, b, "raw", today + 2 * HOUR, {"events": 40, "logins": 1})  # Never rolled up at all
    day = series(theFleet, "90d", now)
    assert day["tier"] == "day"
    assert day["totals"]["events"] == [[today - DAY, 10], [today, 53]]
    assert day["totals"]["logins"] == [[today - DAY, 1], [today, 7]]
    assert day["partial_since"] == today
    hour = series(theFleet, "24h", now, keys=["events", "logins"])
    assert hour["totals"]["events"] == [[today + HOUR, 12], [today + 2 * HOUR, 52], [today + 5 * HOUR, 53]]
    assert hour["totals"]["logins"] == [[today + HOUR, 2], [today + 2 * HOUR, 1], [today + 5 * HOUR, 4]]
    assert hour["partial_since"] == today + 5 * HOUR


def test_a_few_keys_read_from_sqlite_match_whole_rows(db, fleet):
    """Up to EXTRACT_UP_TO keys, the stored rows are read key by key in SQLite instead of decoding their JSON"""
    from application.models.fleetMetrics import EXTRACT_UP_TO
    _, _, theFleet, servers = fleet
    now = BASE + 5 * DAY + 10 * HOUR + 20 * 60
    for index, server in enumerate(servers.values()):
        for hour in range(5):
            add(db, server, "hour", BASE + 5 * DAY + hour * HOUR,
                {"events": 10 * index + hour, "logins": hour % 2, "load_1": 0.5 + hour, "memory_used_pct": 40.5,
                 "flag": True}, samples=6, peaks={"load_1": 2.0 + hour + index, "memory_used_pct": 60})
    few = ["events", "logins", "load_1", "memory_used_pct"]
    assert len(few) <= EXTRACT_UP_TO
    whole = series(theFleet, "7d", now)
    part = series(theFleet, "7d", now, keys=few)
    assert part["totals"] == {key: whole["totals"][key] for key in ("events", "logins")}
    assert part["reporting"] == whole["reporting"]
    for partServer, wholeServer in zip(part["servers"], whole["servers"]):
        assert partServer["sums"] == wholeServer["sums"] == {"logins": 2}
        assert partServer["change"] == wholeServer["change"] == {"events": 4}
        assert partServer["peaks"] == {"load_1": wholeServer["peaks"]["load_1"], "memory_used_pct": 60}
        assert wholeServer["peaks"]["load_1"] >= 6


def test_servers_of_other_fleets_stay_out(db, fleet, make_user):
    from application.DBModels import Fleet, Server
    alice, _, theFleet, servers = fleet
    other = Fleet(name="other", description="", user_id=alice.id, timestamp=1, is_monitored=True)
    db.session.add(other)
    db.session.commit()
    outsider = Server(name="outsider", url="https://out.test", authkey="o" * 40, fleet_id=other.id,
                      user_id=alice.id)
    db.session.add(outsider)
    db.session.commit()
    now = BASE + 5 * DAY
    add(db, servers["a"], "hour", now - 2 * HOUR, {"events": 1})
    add(db, outsider, "hour", now - 2 * HOUR, {"events": 1000})
    add(db, outsider, "raw", now - 60, {"events": 1001})
    answer = series(theFleet, "24h", now, keys=["events"])
    assert answer["totals"]["events"] == [[now - 2 * HOUR, 1]]
    assert answer["latest_ts"] is None
    db.session.delete(outsider)
    db.session.delete(other)
    db.session.commit()


def test_empty_fleet_and_monitoring_off(db, make_user):
    from application.DBModels import Fleet
    user = make_user("fleet-empty@test.local")
    empty = Fleet(name="empty", description="", user_id=user.id, timestamp=1, is_monitored=False)
    db.session.add(empty)
    db.session.commit()
    answer = series(empty, "1y", BASE, keys=["events"], settings=dict(SETTINGS, enabled=False))
    assert answer["totals"] == {"events": []} and answer["reporting"] == [] and answer["servers"] == []
    assert answer["state"] == {"enabled": False, "fleet_monitored": False, "interval_s": 600, "servers": 0}
    assert answer["fleet_servers"] == [] and answer["server_id"] is None
    db.session.delete(empty)
    db.session.commit()


def test_limited_to_one_server(db, fleet, client, auth_headers):
    """`server_id`: the sums, servers and latest sample of that server alone; the picker still gets every server"""
    alice, bob, theFleet, servers = fleet
    a, b = servers["a"], servers["b"]
    h = [BASE + 5 * DAY + n * HOUR for n in range(2)]
    add(db, a, "hour", h[0], {"events": 10, "logins": 2})
    add(db, b, "hour", h[0], {"events": 100, "logins": 3})
    add(db, b, "hour", h[1], {"events": 101, "logins": 1})
    from application.models import fleetMetrics
    _, tier, _ = fleetMetrics.parseRequest("7d", None)
    answer = fleetMetrics.fleetSeries(theFleet, "7d", tier, ["events", "logins"], SETTINGS, now=h[1] + HOUR,
                                      serverId=b.id)
    assert answer["server_id"] == b.id
    assert answer["totals"] == {"events": [[h[0], 100], [h[1], 101]], "logins": [[h[0], 3], [h[1], 1]]}
    assert answer["reporting"] == [[h[0], 1], [h[1], 1]]
    assert [server["name"] for server in answer["servers"]] == ["b-misp"]
    assert answer["servers"][0]["sums"] == {"logins": 4}
    assert answer["fleet_servers"] == [{"id": servers[name].id, "name": f"{name}-misp"} for name in ("a", "b", "c")]
    assert answer["state"]["servers"] == 3
    unfiltered = fleetMetrics.fleetSeries(theFleet, "7d", tier, ["events"], SETTINGS, now=h[1] + HOUR)
    assert unfiltered["server_id"] is None and unfiltered["totals"]["events"] == [[h[0], 110], [h[1], 111]]

    url = f"/fleets/metrics/{theFleet.id}?range=7d&metrics=events"
    response = client.get(f"{url}&server_id={a.id}", headers=auth_headers(alice))
    assert response.status_code == 200 and [server["id"] for server in response.json["servers"]] == [a.id]
    assert len(response.json["fleet_servers"]) == 3
    # Empty: the whole fleet
    assert len(client.get(f"{url}&server_id=", headers=auth_headers(alice)).json["servers"]) == 3
    # A server of another fleet, an unknown one, or no ID at all
    from application.DBModels import Fleet, Server
    other = Fleet(name="other-fleet", description="", user_id=alice.id, timestamp=1)
    db.session.add(other)
    db.session.commit()
    stranger = Server(name="z-misp", url="https://z.test", authkey="k" * 40, fleet_id=other.id, user_id=alice.id)
    db.session.add(stranger)
    db.session.commit()
    try:
        for value, message in ((stranger.id, "not in the fleet"), ("a", "by its ID"), (999999, "not in the fleet")):
            response = client.get(f"{url}&server_id={value}", headers=auth_headers(alice))
            assert response.status_code == 400 and message in response.json["message"]
        # Bob sees no fleet at all, filtered or not
        assert client.get(f"{url}&server_id={a.id}", headers=auth_headers(bob)).status_code == 404
    finally:
        db.session.delete(db.session.get(Server, stranger.id))
        db.session.delete(db.session.get(Fleet, other.id))
        db.session.commit()
