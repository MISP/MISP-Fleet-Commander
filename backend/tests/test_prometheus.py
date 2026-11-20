"""`GET /metrics`: the stored usage metrics in the Prometheus text format"""
import gzip
import re

import pytest

NOW = 1_790_000_000
ENABLED = {"enabled": True, "interval": 600, "max_concurrency": 2}

# The text format 0.0.4: comments, then samples `name{label="value",…} value`, label values escaped
NAME = r"[a-zA-Z_:][a-zA-Z0-9_:]*"
LABEL_VALUE = r'"(?:[^"\\\n]|\\["\\n])*"'
LABEL = rf"[a-zA-Z_]\w*={LABEL_VALUE}"
SAMPLE_RE = re.compile(rf"^(?P<name>{NAME})(?:\{{(?P<labels>{LABEL}(?:,{LABEL})*)\}})?"
                       rf" (?P<value>-?\d+(?:\.\d+)?(?:e[+-]?\d+)?|NaN|[+-]Inf)$")
LABEL_RE = re.compile(rf"(?P<name>[a-zA-Z_]\w*)=(?P<value>{LABEL_VALUE})")
COMMENT_RE = re.compile(rf"^# (?:HELP (?P<help>{NAME}) [^\n]*|TYPE (?P<type>{NAME}) (?:gauge|counter))$")


def unescape(quoted: str) -> str:
    return re.sub(r"\\(.)", lambda match: {"n": "\n"}.get(match[1], match[1]), quoted[1:-1])


def parse(text: str) -> dict:
    """{(name, frozenset of labels): value}, checking each line against the format and that a family's lines
    follow each other, after its HELP and TYPE"""
    assert text.endswith("\n")
    samples, seen, current = {}, set(), None
    for line in text.splitlines():
        comment = COMMENT_RE.match(line)
        if comment:
            name = comment["help"] or comment["type"]
            if name != current:
                assert name not in seen, f"{name} is not grouped"
                seen.add(name)
                current = name
            continue
        match = SAMPLE_RE.match(line)
        assert match, f"Not in the text format: {line!r}"
        assert match["name"] == current, f"{match['name']} has no HELP/TYPE before it"
        labels = frozenset((label["name"], unescape(label["value"]))
                           for label in LABEL_RE.finditer(match["labels"] or ""))
        key = (match["name"], labels)
        assert key not in samples, f"Duplicate sample {key}"
        samples[key] = float(match["value"])
    return samples


def labelled(server, fleet, **extra):
    return frozenset({("server", server.name), ("server_id", str(server.id)), ("fleet", fleet.name), *extra.items()})


@pytest.fixture()
def fleets(db, make_user, monkeypatch):
    """Alice's monitored fleet (a collected server, one whose last collection failed, one never collected), her
    fleet that is not monitored, and Bob's monitored fleet. Names hold the characters the format escapes"""
    from application import redisModel
    from application.DBModels import Fleet, MetricSample, MetricState, Server
    import application.models.metrics as metricModel

    monkeypatch.setattr(metricModel, "monitoringSettings", lambda: dict(ENABLED))
    alice, bob = make_user("prom-alice@test.local"), make_user("prom-bob@test.local")
    monitored = Fleet(name='Prod "EU"\\core', description="", user_id=alice.id, timestamp=1, is_monitored=True)
    quiet = Fleet(name="Quiet", description="", user_id=alice.id, timestamp=1, is_monitored=False)
    bobs = Fleet(name="Bob's", description="", user_id=bob.id, timestamp=1, is_monitored=True)
    db.session.add_all([monitored, quiet, bobs])
    db.session.commit()

    def server(name, fleet, user):
        row = Server(name=name, url=f"https://{len(name)}.test", authkey="k" * 40, fleet_id=fleet.id, user_id=user.id)
        db.session.add(row)
        db.session.commit()
        return row

    collected = server('misp "one"\nline\\2', monitored, alice)
    failing = server("misp-failing", monitored, alice)
    fresh = server("misp-fresh", monitored, alice)
    unmonitored = server("misp-unmonitored", quiet, alice)
    bobsServer = server("misp-bob", bobs, bob)

    db.session.add_all([
        MetricSample(server_id=collected.id, tier="raw", ts=NOW - 1200, values={"events": 1, "load_1": 9.0}),
        MetricSample(server_id=collected.id, tier="raw", ts=NOW - 600, values={
            "events": 4291, "attributes": 120_000, "logins": 3, "load_1": 0.42, "memory_used_pct": 77.27,
            "disk_used_pct": 50, "db_size_bytes": 9_325_838_745, "queue_default": 2, "queue_prio": 0,
        }),
        MetricSample(server_id=collected.id, tier="hour", ts=NOW - NOW % 3600, values={"events": 99999}, samples=6),
        MetricSample(server_id=failing.id, tier="raw", ts=NOW - 7200, values={"events": 10}),
        MetricSample(server_id=unmonitored.id, tier="raw", ts=NOW - 600, values={"events": 5}),
        MetricSample(server_id=bobsServer.id, tier="raw", ts=NOW - 600, values={"events": 6}),
        MetricState(server_id=collected.id, last_attempt=NOW - 600, last_success=NOW - 600, logins_total=1500,
                    failed_logins_total=12, logins_backfilled=True, logins_read_at=NOW - 600),
        MetricState(server_id=failing.id, last_attempt=NOW - 600, last_success=NOW - 7200,
                    last_error="Server unreachable", logins_total=0, failed_logins_total=0),
        MetricState(server_id=unmonitored.id, last_attempt=NOW - 600, last_success=NOW - 600),
        MetricState(server_id=bobsServer.id, last_attempt=NOW - 600, last_success=NOW - 600),
    ])
    db.session.commit()
    redisModel.saveServerStatus(collected.uuid, {"version": "3.0.0", "timestamp": NOW})
    redisModel.saveServerStatus(failing.uuid, {"error": "Server unreachable", "timestamp": NOW})

    yield {"alice": alice, "bob": bob, "monitored": monitored, "bobs": bobs, "collected": collected,
           "failing": failing, "fresh": fresh, "unmonitored": unmonitored, "bobsServer": bobsServer}
    for row in (collected, failing, fresh, unmonitored, bobsServer):
        redisModel.deleteServerData(row.uuid, row.id)
        db.session.delete(row)
    for row in (monitored, quiet, bobs):
        db.session.delete(row)
    db.session.commit()


@pytest.fixture()
def no_misp(monkeypatch):
    """A scrape must not query MISP"""
    import requests.adapters

    def refuse(*args, **kwargs):
        raise AssertionError("A scrape queried MISP")
    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", refuse)


def scrape(client, headers):
    answer = client.get("/metrics", headers=headers)
    assert answer.status_code == 200, answer.get_data(as_text=True)
    assert answer.headers["Content-Type"] == "text/plain; version=0.0.4; charset=utf-8"
    return parse(answer.get_data(as_text=True))


def test_serves_the_latest_sample_of_monitored_servers(client, auth_headers, fleets, no_misp):
    collected, failing, fleet = fleets["collected"], fleets["failing"], fleets["monitored"]
    samples = scrape(client, auth_headers(fleets["alice"]))
    one, two = labelled(collected, fleet), labelled(failing, fleet)

    assert samples[("mfc_monitoring_enabled", frozenset())] == 1
    assert samples[("misp_up", one)] == 1
    assert samples[("misp_up", two)] == 0
    assert samples[("misp_last_sample_timestamp_seconds", one)] == NOW - 600
    assert samples[("misp_last_sample_timestamp_seconds", two)] == NOW - 7200
    assert samples[("misp_info", labelled(collected, fleet, version="3.0.0"))] == 1
    assert not any(name == "misp_info" and ("server_id", str(failing.id)) in labels for name, labels in samples)

    # The newest raw sample only: not an older one, not the hour roll-up
    assert samples[("misp_events", one)] == 4291
    assert samples[("misp_attributes", one)] == 120_000
    assert samples[("misp_load_1", one)] == 0.42
    assert samples[("misp_db_size_bytes", one)] == 9_325_838_745
    assert samples[("misp_memory_used_ratio", one)] == 0.7727
    assert samples[("misp_disk_used_ratio", one)] == 0.5
    assert samples[("misp_queue_jobs", labelled(collected, fleet, queue="default"))] == 2
    assert samples[("misp_queue_jobs", labelled(collected, fleet, queue="prio"))] == 0
    assert samples[("misp_events", two)] == 10
    # Keys the sample doesn't have are left out, and logins are counters from the running totals
    assert ("misp_objects", one) not in samples and ("misp_load_1", two) not in samples
    assert not any(name in ("misp_logins", "misp_memory_used_pct", "misp_queue_default") for name, _ in samples)
    assert samples[("misp_logins_total", one)] == 1500
    assert samples[("misp_failed_logins_total", one)] == 12
    # Logs never read: no counter yet, so that the backfilled total doesn't show up as new logins later
    assert ("misp_logins_total", two) not in samples and ("misp_failed_logins_total", two) not in samples

    # Never collected, not monitored, someone else's: absent
    servers = {dict(labels).get("server_id") for _, labels in samples} - {None}
    assert servers == {str(collected.id), str(failing.id)}


def test_types_and_help(client, auth_headers, fleets):
    text = client.get("/metrics", headers=auth_headers(fleets["alice"])).get_data(as_text=True)
    assert "# TYPE misp_logins_total counter\n" in text
    assert "# TYPE misp_events gauge\n" in text
    assert "# HELP misp_memory_used_ratio Memory used (0 to 1)\n" in text
    assert "# HELP misp_db_size_bytes Database size (bytes)\n" in text
    assert text.count("# TYPE misp_queue_jobs gauge") == 1


def test_label_values_are_escaped(client, auth_headers, fleets):
    text = client.get("/metrics", headers=auth_headers(fleets["alice"])).get_data(as_text=True)
    assert 'server="misp \\"one\\"\\nline\\\\2"' in text
    assert 'fleet="Prod \\"EU\\"\\\\core"' in text


def test_scoped_to_the_requester(client, auth_headers, fleets):
    bobsServer, bobs = fleets["bobsServer"], fleets["bobs"]
    samples = scrape(client, auth_headers(fleets["bob"]))
    assert {dict(labels).get("server_id") for _, labels in samples} - {None} == {str(bobsServer.id)}
    assert samples[("misp_events", labelled(bobsServer, bobs))] == 6


def test_authentication(client, db, fleets):
    alice = fleets["alice"]
    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics", headers={"Authorization": "Apikey nope"}).status_code == 401
    key = "prometheus-scrape-key-" + "x" * 30
    alice.setAPIKey(key)
    db.session.commit()
    try:
        samples = scrape(client, {"Authorization": f"Apikey {key}"})
        assert samples[("misp_up", labelled(fleets["collected"], fleets["monitored"]))] == 1
    finally:
        alice.setAPIKey(None)
        db.session.commit()


def test_nothing_from_servers_while_monitoring_is_off(client, auth_headers, fleets, monkeypatch):
    import application.models.metrics as metricModel
    monkeypatch.setattr(metricModel, "monitoringSettings", lambda: dict(ENABLED, enabled=False))
    answer = client.get("/metrics", headers=auth_headers(fleets["alice"]))
    # Saved queries run whether monitoring is on or not
    assert parse(answer.get_data(as_text=True)) == {("mfc_monitoring_enabled", frozenset()): 0,
                                                    ("mfc_saved_query_schedule_enabled", frozenset()): 1}


def test_formatting():
    from application.models.prometheus import Exposition, formatValue
    assert [formatValue(value) for value in (3, True, 0.5, 1e20, float("nan"), float("inf"), -float("inf"))] == \
        ["3", "1", "0.5", "1e+20", "NaN", "+Inf", "-Inf"]
    out = Exposition()
    out.add("a", "gauge", "Line\nand \\", (), 1)
    assert out.render() == "# HELP a Line\\nand \\\\\n# TYPE a gauge\na 1\n"


def test_large_answers_are_compressed(app):
    from flask import Response
    from application.compression import compressResponse
    text = "misp_events{server=\"x\"} 1\n" * 2000
    with app.test_request_context(headers={"Accept-Encoding": "gzip"}):
        response = Response(text, content_type="text/plain; version=0.0.4; charset=utf-8")
        response = compressResponse(response)
        assert response.headers["Content-Encoding"] == "gzip"
        assert gzip.decompress(response.get_data()).decode() == text
