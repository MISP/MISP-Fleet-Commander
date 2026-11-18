"""Hourly and daily roll-ups of the metric samples, and retention"""
from types import SimpleNamespace

import pytest

HOUR = 3600
DAY = 24 * HOUR
BASE = 1_790_000_000 - 1_790_000_000 % DAY  # A UTC midnight


@pytest.fixture(autouse=True)
def _app(app):
    """The roll-ups import the models, which need the app first"""


@pytest.fixture()
def server(db, make_user):
    from application.DBModels import Fleet, Server
    user = make_user("rollups@test.local")
    fleet = Fleet(name="rollups", description="", user_id=user.id, timestamp=1, is_monitored=True)
    db.session.add(fleet)
    db.session.commit()
    theServer = Server(name="rollups-misp", url="https://rollups.test", authkey="r" * 40, fleet_id=fleet.id,
                       user_id=user.id)
    db.session.add(theServer)
    db.session.commit()
    yield theServer
    db.session.delete(theServer)
    db.session.delete(fleet)
    db.session.commit()


def add(db, server, tier, ts, values, samples=1, peaks=None):
    from application.DBModels import MetricSample
    db.session.add(MetricSample(server_id=server.id, tier=tier, ts=ts, values=values, samples=samples, peaks=peaks))
    db.session.commit()


def rows(server, tier):
    from application.DBModels import MetricSample
    return {row.ts: row for row in MetricSample.query.filter_by(server_id=server.id, tier=tier)}


def test_bucket_maths():
    from application.models.metricRollups import summarise
    row = lambda ts, values, samples=1, peaks=None: SimpleNamespace(ts=ts, values=values, samples=samples, peaks=peaks)
    # Raw rows: last total, summed deltas, averaged gauges with their maximum. Unknown keys and junk are dropped
    values, peaks, samples = summarise([
        row(20, {"events": 12, "load_1": 3.0, "logins": 1}),
        row(10, {"events": 10, "load_1": 1.0, "logins": 2, "gone_metric": 4, "users": "x"}),
        row(30, {"load_1": 2.0, "redis_memory_bytes": 1001}),
        row(40, {"load_1": 2.0, "redis_memory_bytes": 1002}),
    ])
    assert values == {"events": 12, "load_1": 2.0, "logins": 3, "redis_memory_bytes": 1002}  # Whole bytes
    assert peaks == {"load_1": 3.0, "redis_memory_bytes": 1002} and samples == 4
    # Hour rows: gauges weighted by the samples behind them; backfilled login hours have none
    values, peaks, samples = summarise([
        row(0, {"load_1": 2.0, "logins": 3}, samples=6, peaks={"load_1": 5.0}),
        row(3600, {"load_1": 4.0, "logins": 1}, samples=2, peaks={"load_1": 4.5}),
        row(7200, {"logins": 5, "failed_logins": 1}, samples=0),
    ])
    assert values == {"load_1": 2.5, "logins": 9, "failed_logins": 1}
    assert peaks == {"load_1": 5.0} and samples == 8


def test_hours_and_days_are_rolled_up_once_over(db, server):
    from application.models import metricRollups
    add(db, server, "hour", BASE + 3 * HOUR, {"logins": 5, "failed_logins": 1}, samples=0)  # Backfilled
    add(db, server, "raw", BASE + 10 * HOUR, {"events": 10, "load_1": 1.0, "logins": 2})
    add(db, server, "raw", BASE + 10 * HOUR + 600, {"events": 12, "load_1": 3.0, "logins": 1})
    add(db, server, "raw", BASE + 10 * HOUR + 3000, {"events": 13, "load_1": 2.0})
    add(db, server, "raw", BASE + 11 * HOUR + 300, {"events": 15, "load_1": 5.0, "logins": 4})

    metricRollups.run(BASE + 11 * HOUR + 1800)
    hours = rows(server, "hour")
    assert sorted(hours) == [BASE + 3 * HOUR, BASE + 10 * HOUR]  # 11:00 is not over
    hour = hours[BASE + 10 * HOUR]
    assert hour.values == {"events": 13, "load_1": 2.0, "logins": 3}
    assert hour.peaks == {"load_1": 3.0} and hour.samples == 3
    assert rows(server, "day") == {}

    metricRollups.run(BASE + DAY + 7 * 60)
    hours = rows(server, "hour")
    assert hours[BASE + 11 * HOUR].values == {"events": 15, "load_1": 5.0, "logins": 4}
    day, = rows(server, "day").values()
    assert day.ts == BASE
    assert day.values == {"events": 15, "load_1": 2.75, "logins": 12, "failed_logins": 1}
    assert day.peaks == {"load_1": 5.0} and day.samples == 4
    assert len(rows(server, "raw")) == 4  # Kept for 14 days

    # Running again changes nothing
    metricRollups.run(BASE + DAY + 7 * 60)
    assert len(rows(server, "hour")) == 3 and len(rows(server, "day")) == 1
    assert rows(server, "day")[BASE].values == day.values


def test_old_rows_are_rolled_up_before_they_go(db, server):
    from application.models import metricRollups
    now = BASE + 200 * DAY + 7 * 60
    add(db, server, "raw", now - 20 * DAY, {"events": 1})
    add(db, server, "raw", now - 3 * DAY, {"events": 2})
    add(db, server, "hour", BASE + 100 * DAY, {"logins": 2}, samples=0)
    add(db, server, "day", BASE + 50 * DAY, {"events": 0}, samples=144)
    report = metricRollups.run(now)
    assert [row.values for row in rows(server, "raw").values()] == [{"events": 2}]
    assert {ts: row.values for ts, row in rows(server, "hour").items()} == {
        BASE + 180 * DAY: {"events": 1}, BASE + 197 * DAY: {"events": 2}}
    assert {ts: row.values for ts, row in rows(server, "day").items()} == {
        BASE + 50 * DAY: {"events": 0}, BASE + 100 * DAY: {"logins": 2}, BASE + 180 * DAY: {"events": 1},
        BASE + 197 * DAY: {"events": 2}}
    assert report["deleted"]["raw"] >= 1 and report["deleted"]["hour"] >= 1


def test_no_day_from_hours_that_failed(db, server, monkeypatch):
    from application.models import metricRollups
    add(db, server, "hour", BASE + 2 * HOUR, {"logins": 1}, samples=0)
    add(db, server, "raw", BASE + 5 * HOUR, {"events": 3})
    original = metricRollups.rollupServer

    def failing(server_id, sourceTier, *args):
        if server_id == server.id and sourceTier == "raw":
            raise RuntimeError("disk full")
        return original(server_id, sourceTier, *args)
    monkeypatch.setattr(metricRollups, "rollupServer", failing)
    metricRollups.run(BASE + DAY + 7 * 60)
    assert rows(server, "day") == {}
    monkeypatch.setattr(metricRollups, "rollupServer", original)
    metricRollups.run(BASE + DAY + 7 * 60)
    assert rows(server, "day")[BASE].values == {"logins": 1, "events": 3}
