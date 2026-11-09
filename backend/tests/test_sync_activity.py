"""Sync activity: pulls and pushes per sync server read from MISP's logs, across the log formats of MISP 2.4 to 3.0,
and the cached, owner-scoped endpoint serving them"""
import pytest

NOW = 2_000_000_000
DAY = 24 * 3600

# Change texts as MISP writes them, oldest version first
PULL_2_4 = "2 events, 1 proposals and 3 sightings pulled or updated. 4 events failed or didn't need an update."
PULL_2_4_CLUSTERS = ("5 events, 0 proposals, 1 sightings and 2 galaxyClusters pulled or updated. "
                     "0 events failed or didn't need an update.")
PULL_2_5 = ("2 events, 0 proposals, 0 sightings, 0 galaxy clusters and 2 analyst data pulled or updated. "
            "1 events failed or didn't need an update.")
PULL_3_0 = ("7 events, 1 proposals, 2 sightings, 3 galaxy clusters, 4 analyst data and 5 collections pulled or "
            "updated. 6 events failed or didn't need an update.")
PUSH_OLD = "2 events pushed or updated. 2 events failed or didn't need an update."
PUSH_3_0 = "3 events pushed or updated. 1 events failed or didn't need an update. 4 collections pushed."


def created(ts):
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def log(ts, remote_id, title, change="", action="pull"):
    return {"Log": {"id": str(ts), "created": created(ts), "model": "Server", "model_id": str(remote_id),
                    "action": action, "title": title, "change": change}}


def pull(ts, remote_id, change=PULL_3_0, url=None):
    return log(ts, remote_id, f"Pull from {url or f'https://r{remote_id}.test'} initiated by Scheduled job", change)


def push(ts, remote_id, change=PUSH_3_0):
    return log(ts, remote_id, f"Push to https://r{remote_id}.test initiated by admin@misp.test", change, "push")


def failedPull(ts, remote_id, reason="curl error 7 'Couldn't connect to server'"):
    return log(ts, remote_id, f"Failed pull from https://r{remote_id}.test initiated by Scheduled job", reason, "error")


def failedPush(ts, remote_id, reason="Error: Connection to the server has failed."):
    return log(ts, remote_id, f"Failed: Push to https://r{remote_id}.test initiated by admin@misp.test",
               f"Push to server {remote_id} failed. Reason: {reason}", "error")


@pytest.mark.parametrize("change, expected", [
    (PULL_2_4, {"events": 2, "proposals": 1, "sightings": 3, "galaxy_clusters": 0, "analyst_data": 0,
                "collections": 0, "events_failed": 4}),
    (PULL_2_4_CLUSTERS, {"events": 5, "proposals": 0, "sightings": 1, "galaxy_clusters": 2, "analyst_data": 0,
                         "collections": 0, "events_failed": 0}),
    (PULL_2_5, {"events": 2, "proposals": 0, "sightings": 0, "galaxy_clusters": 0, "analyst_data": 2,
                "collections": 0, "events_failed": 1}),
    (PULL_3_0, {"events": 7, "proposals": 1, "sightings": 2, "galaxy_clusters": 3, "analyst_data": 4,
                "collections": 5, "events_failed": 6}),
    ("1 event, 0 proposals and 0 sightings pulled or updated. 1 event failed or didn't need an update.",
     {"events": 1, "proposals": 0, "sightings": 0, "galaxy_clusters": 0, "analyst_data": 0, "collections": 0,
      "events_failed": 1}),
])
def test_pull_change_formats(app, change, expected):
    from application.models.syncActivity import parsePullChange
    assert parsePullChange(change) == expected


@pytest.mark.parametrize("change", ["", None, "Reason: timeout", "something pulled or updated."])
def test_unreadable_pull_change(app, change):
    from application.models.syncActivity import parsePullChange
    assert parsePullChange(change) is None


@pytest.mark.parametrize("change, expected", [
    (PUSH_OLD, {"events": 2, "events_failed": 2, "collections": 0}),
    (PUSH_3_0, {"events": 3, "events_failed": 1, "collections": 4}),
    ("Pushed", None),
])
def test_push_change_formats(app, change, expected):
    from application.models.syncActivity import parsePushChange
    assert parsePushChange(change) == expected


def test_groups_runs_by_remote(app):
    from application.models.syncActivity import parseSyncLogs
    entries = [
        pull(NOW - 3 * DAY, 6, PULL_2_5),
        pull(NOW - 3600, 6, PULL_3_0),
        failedPull(NOW - 1800, 6),
        push(NOW - 2 * DAY, 5, PUSH_OLD),
        failedPush(NOW - 600, 5),
        failedPush(NOW - 300, 7, "remote said no"),
    ]
    remotes = parseSyncLogs(entries, NOW)
    assert [remote["remote_server_id"] for remote in remotes] == [5, 6, 7]
    r5, r6, r7 = remotes

    assert r6["url"] == "https://r6.test" and r6["push"] is None
    pulls = r6["pull"]
    assert (pulls["runs"], pulls["failures"]) == (3, 1)
    assert pulls["last_run"] == NOW - 1800
    assert pulls["last_success"] == NOW - 3600
    assert pulls["last_failure"] == NOW - 1800
    assert pulls["last_error"] == "curl error 7 'Couldn't connect to server'"
    assert pulls["totals"] == {"events": 9, "proposals": 1, "sightings": 2, "galaxy_clusters": 3, "analyst_data": 6,
                               "collections": 5, "events_failed": 7}

    assert r5["pull"] is None
    pushes = r5["push"]
    assert (pushes["runs"], pushes["failures"]) == (2, 1)
    assert pushes["totals"] == {"events": 2, "events_failed": 2, "collections": 0}
    # MISP's "Push to server N failed. Reason:" prefix is dropped
    assert pushes["last_error"] == "Error: Connection to the server has failed."

    assert r7["push"]["last_success"] is None and r7["push"]["last_error"] == "remote said no"


def test_daily_buckets(app):
    """Seven 24-hour buckets, oldest first; the last one covers the past 24 hours"""
    from application.models.syncActivity import parseSyncLogs
    entries = [
        pull(NOW - 7 * DAY + 60, 1, PULL_2_4),   # first bucket: 2 events
        pull(NOW - 10, 1, PULL_3_0),             # last bucket: 7 events
        pull(NOW - 20, 1, PULL_3_0),
        failedPull(NOW - DAY - 5, 1),            # second to last bucket
    ]
    daily = parseSyncLogs(entries, NOW)[0]["pull"]["daily"]
    assert len(daily) == 7
    assert daily[0] == {"runs": 1, "failures": 0, "events": 2}
    assert daily[5] == {"runs": 1, "failures": 1, "events": 0}
    assert daily[6] == {"runs": 2, "failures": 0, "events": 14}
    assert sum(bucket["runs"] for bucket in daily[1:5]) == 0


def test_ignored_entries(app):
    from application.models.syncActivity import parseSyncLogs
    entries = [
        pull(NOW - 8 * DAY, 1),                                                     # outside the window
        pull(NOW + 60, 1),                                                          # in the future
        log(NOW - 60, 1, "Failed to pull event #12.", "Reason: Blocked by rules"),  # per-event failure
        log(NOW - 60, 1, "Error: Connection to the server has failed.", "", "error"),
        log(NOW - 60, "", "Pull from https://r.test initiated by x", PULL_3_0),     # no sync server id
        log(NOW - 60, 1, "Pull from https://r.test initiated by x", "Unreadable"),
        {"Log": {"created": "yesterday", "model_id": "1", "title": "Pull from https://r.test initiated by x",
                 "change": PULL_3_0}},
        "not an entry",
    ]
    assert parseSyncLogs(entries, NOW) == []


def test_url_follows_the_latest_run(app):
    from application.models.syncActivity import parseSyncLogs
    entries = [pull(NOW - 60, 3, url="https://new.test"), pull(NOW - 3600, 3, url="https://old.test")]
    assert parseSyncLogs(entries, NOW)[0]["url"] == "https://new.test"


def test_long_errors_are_shortened(app):
    from application.models.syncActivity import parseSyncLogs
    error = parseSyncLogs([failedPull(NOW - 60, 1, "x" * 1000)], NOW)[0]["pull"]["last_error"]
    assert len(error) == 300 and error.endswith("…")


# Endpoint

@pytest.fixture()
def owned(db, make_user):
    from application import redisModel
    from application.DBModels import Fleet, Server
    alice = make_user("sync-alice@test.local")
    bob = make_user("sync-bob@test.local")
    fleet = Fleet(name="Sync", description="", user_id=alice.id, timestamp=1)
    db.session.add(fleet)
    db.session.commit()
    server = Server(name="hub", url="https://hub.test", authkey="k" * 40, fleet_id=fleet.id, user_id=alice.id)
    db.session.add(server)
    db.session.commit()
    yield alice, bob, server
    redisModel.redisClient.delete(f"sync-activity:{server.id}")
    db.session.delete(server)
    db.session.commit()
    db.session.delete(fleet)
    db.session.commit()


@pytest.fixture()
def misp(monkeypatch):
    """Fake `/admin/logs/index`: `answer` is returned (lists wrapped as the request helper does); `requests` keeps
    the payloads and options it was called with"""
    import application.models.syncActivity as syncActivity
    state = {"answer": [pull(NOW - 60, 6)], "requests": []}

    def fakePost(server, url, data={}, rawResponse=False, nocache=True, timeout=None):
        state["requests"].append({"url": url, "data": data, "timeout": timeout})
        answer = state["answer"]
        if callable(answer):
            answer = answer(data)
        if isinstance(answer, list):
            return {"data": answer, "_latency": 0.1, "_status_code": 200}
        return answer
    monkeypatch.setattr(syncActivity, "mispPostRequest", fakePost)
    monkeypatch.setattr(syncActivity.time, "time", lambda: NOW)
    return state


def test_endpoint_reads_the_logs(client, auth_headers, owned, misp):
    alice, _, server = owned
    response = client.get(f"/servers/syncOvertime/{server.id}", headers=auth_headers(alice))
    assert response.status_code == 200
    body = response.get_json()
    assert body["server_id"] == server.id and body["timestamp"] == NOW
    assert body["window_days"] == 7 and body["truncated"] is False and body["cached"] is False
    assert [remote["remote_server_id"] for remote in body["remotes"]] == [6]
    request = misp["requests"][0]
    assert request["url"] == "/admin/logs/index" and request["timeout"] == 30
    assert request["data"]["model"] == "Server" and request["data"]["created"] == "7d"
    assert set(request["data"]["title"]) == {"Pull from %", "Push to %", "Failed pull from %", "Failed: Push to %"}


def test_endpoint_is_scoped_to_the_owner(client, auth_headers, owned, misp):
    _, bob, server = owned
    assert client.get(f"/servers/syncOvertime/{server.id}", headers=auth_headers(bob)).status_code == 404
    assert client.get("/servers/syncOvertime/999999", headers=auth_headers(bob)).status_code == 404
    assert client.get(f"/servers/syncOvertime/{server.id}").status_code == 401
    assert misp["requests"] == []


def test_endpoint_caches_until_refresh(client, auth_headers, owned, misp):
    alice, _, server = owned
    headers = auth_headers(alice)
    client.get(f"/servers/syncOvertime/{server.id}", headers=headers)
    misp["answer"] = []
    cached = client.get(f"/servers/syncOvertime/{server.id}", headers=headers).get_json()
    assert cached["cached"] is True and len(cached["remotes"]) == 1
    assert len(misp["requests"]) == 1
    fresh = client.get(f"/servers/syncOvertime/{server.id}?refresh=1", headers=headers).get_json()
    assert fresh["cached"] is False and fresh["remotes"] == []
    assert len(misp["requests"]) == 2


@pytest.mark.parametrize("answer, message", [
    ({"error": "Authentication error", "_status_code": 403}, "MISP refused to list its logs: the API key needs admin rights"),
    ({"name": "Not Found", "message": "Not Found", "_status_code": 404}, "This MISP cannot search its logs through the API"),
    ({"error": "Request timed out"}, "Request timed out"),
    ({"error": "Exception Expecting value"}, "Unexpected answer from MISP"),
])
def test_errors_are_readable_and_not_cached(client, auth_headers, owned, misp, answer, message):
    alice, _, server = owned
    headers = auth_headers(alice)
    misp["answer"] = answer
    body = client.get(f"/servers/syncOvertime/{server.id}", headers=headers).get_json()
    assert body["error"] == message and "remotes" not in body
    misp["answer"] = [pull(NOW - 60, 6)]
    body = client.get(f"/servers/syncOvertime/{server.id}", headers=headers).get_json()
    assert "error" not in body and len(body["remotes"]) == 1


def test_busy_log_falls_back_to_the_last_day(client, auth_headers, owned, misp, monkeypatch):
    """The API returns the oldest entries first: when the week does not fit, the last day is read instead"""
    import application.models.syncActivity as syncActivity
    monkeypatch.setattr(syncActivity, "MAX_ENTRIES", 3)
    alice, _, server = owned
    misp["answer"] = lambda data: [pull(NOW - 6 * DAY, 1)] * 3 if data["created"] == "7d" else [pull(NOW - 60, 2)]
    body = client.get(f"/servers/syncOvertime/{server.id}", headers=auth_headers(alice)).get_json()
    assert [request["data"]["created"] for request in misp["requests"]] == ["7d", "1d"]
    assert body["window_days"] == 1 and body["truncated"] is False
    assert [remote["remote_server_id"] for remote in body["remotes"]] == [2]
    assert len(body["remotes"][0]["pull"]["daily"]) == 1

    misp["requests"].clear()
    misp["answer"] = lambda data: [pull(NOW - 60, 1)] * 3
    body = client.get(f"/servers/syncOvertime/{server.id}?refresh=1", headers=auth_headers(alice)).get_json()
    assert body["window_days"] == 1 and body["truncated"] is True


def test_cache_goes_with_the_server(app, owned, misp):
    from application import redisModel
    from application.models.syncActivity import getSyncActivity
    _, _, server = owned
    getSyncActivity(server)
    assert redisModel.redisClient.exists(f"sync-activity:{server.id}")
    redisModel.deleteServerData(server.uuid, server.id)
    assert not redisModel.redisClient.exists(f"sync-activity:{server.id}")
