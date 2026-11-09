"""Server data stays available and fresh without the UI: snapshots never expire, connection tests are persisted and
background tasks keep every server up to date"""
import time

import pytest


@pytest.fixture(autouse=True)
def _fake_redis(app):
    """The app fixture swaps in the fake Redis: every test here needs it, even those not touching the app"""


@pytest.fixture()
def servers(db, make_user):
    """Two users, each with a fleet and servers. One server has no API key"""
    from application.DBModels import Fleet, Server

    created = {}
    for email in ("bg-alice@test.local", "bg-bob@test.local"):
        user = make_user(email)
        fleet = Fleet(name=f"Fleet of {email}", description="", user_id=user.id, timestamp=1)
        db.session.add(fleet)
        db.session.commit()
        created[email] = (user, fleet, [])
    alice, aliceFleet, aliceServers = created["bg-alice@test.local"]
    bob, bobFleet, bobServers = created["bg-bob@test.local"]
    for name, user, fleet, bucket, authkey in (
        ("alice-1", alice, aliceFleet, aliceServers, "a" * 40),
        ("alice-nokey", alice, aliceFleet, aliceServers, None),
        ("bob-1", bob, bobFleet, bobServers, "b" * 40),
    ):
        server = Server(name=name, url=f"https://{name}.test", authkey=authkey, fleet_id=fleet.id, user_id=user.id)
        db.session.add(server)
        db.session.commit()
        bucket.append(server)
    yield created
    for user, fleet, bucket in created.values():
        for server in bucket:
            if server in db.session:
                db.session.delete(server)
        db.session.delete(fleet)
    db.session.commit()


@pytest.fixture()
def emitted(monkeypatch):
    import application.workers.tasks as tasks
    events = []
    monkeypatch.setattr(tasks.socketioEmitter.socketio, "emit",
                        lambda event, data=None, **kw: events.append((event, data, kw.get("to"))))
    return events


@pytest.fixture()
def bg_settings(monkeypatch):
    import application.workers.tasks as tasks
    config = {"enabled": True, "connection_test_interval": 5 * 60, "full_refresh_interval": 30 * 60, "max_concurrency": 2}
    monkeypatch.setattr(tasks, "backgroundRefreshSettings", lambda: dict(config))
    return config


def test_snapshots_never_expire():
    from application import redisModel, redisClient
    redisModel.saveServerInfo("uuid-no-ttl", {"timestamp": 1, "query_result": {}})
    assert redisClient.ttl("server-info:uuid-no-ttl") == -1


def test_partial_save_works_on_old_snapshots(servers):
    """It used to do nothing once the snapshot had expired"""
    import application.models.servers as serverModel
    from application import redisModel
    server = servers["bg-alice@test.local"][2][0]
    redisModel.saveServerInfo(server.uuid, {"timestamp": int(time.time()) - 2 * 3600, "query_result": {}})
    assert serverModel.savePartialInfo(server, "serverUsage", {"users": 3})
    assert redisModel.getServerInfo(server.uuid)["query_result"]["serverUsage"] == {"users": 3}


def test_connection_test_is_persisted(monkeypatch, servers):
    import application.models.servers as serverModel
    from application import redisModel
    server = servers["bg-alice@test.local"][2][0]
    monkeypatch.setattr(serverModel, "mispGetRequest", lambda *a, **kw: {
        "version": "2.5.1", "perm_sync": True, "_latency": 0.12, "_status_code": 200})

    result = serverModel.testConnection(server.id)

    status = redisModel.getServerStatus(server.uuid)
    assert status == {"version": "2.5.1", "_latency": 0.12, "_status_code": 200, "timestamp": result["timestamp"]}


def test_connection_tests_asked_from_the_ui_time_out_like_background_ones(monkeypatch, servers):
    """A server that does not answer must not keep a worker busy for minutes"""
    import application.models.servers as serverModel
    server = servers["bg-alice@test.local"][2][0]
    timeouts = []

    async def fakeFetcher(srv, urls, timeout=300):
        timeouts.append(timeout)
        return [{"error": f"Timeout Exception ({timeout}s)"}]

    async def fakeManyFetcher(srvs, url, callback, timeout=300, max_concurrency=None):
        timeouts.append(timeout)
    monkeypatch.setattr(serverModel, "asyncFetcher", fakeFetcher)
    monkeypatch.setattr(serverModel, "asyncFetcherManyServer", fakeManyFetcher)

    serverModel.testConnectionAsync(server.id)  # "Test connection" on one server
    serverModel.testAllConnectionAsync([server], lambda *a: None)  # "Quick refresh" of a fleet
    assert timeouts == [serverModel.CONNECTION_TEST_TIMEOUT] * 2 and serverModel.CONNECTION_TEST_TIMEOUT == 30


def test_non_json_connection_test_is_stored_as_error(servers):
    from application import redisModel
    server = servers["bg-alice@test.local"][2][0]
    status = redisModel.saveServerStatus(server.uuid, "<html>Bad gateway</html>")
    assert "Bad gateway" in status["error"]


def test_connection_status_is_returned_to_the_owner(client, auth_headers, servers):
    from application import redisModel
    alice, fleet, (server, *_) = servers["bg-alice@test.local"]
    redisModel.saveServerStatus(server.uuid, {"error": "Server unreachable", "timestamp": 42})

    response = client.get(f"/servers/index/{fleet.id}", headers=auth_headers(alice))

    assert response.status_code == 200
    byID = {s["id"]: s for s in response.json}
    assert byID[server.id]["connection_status"] == {"error": "Server unreachable", "timestamp": 42}


def test_deleting_a_server_forgets_its_cached_data(db, servers):
    from application import redisModel, redisClient
    server = servers["bg-bob@test.local"][2][0]
    uuid = server.uuid
    redisModel.saveServerInfo(uuid, {"timestamp": 1, "query_result": {}})
    redisModel.saveServerStatus(uuid, {"version": "2.5.1"})
    redisModel.setServerWatchedTimestamp(uuid)

    db.session.delete(server)
    db.session.commit()

    assert [key for key in redisClient.keys(f"*:{uuid}")] == []


def test_due_servers(servers):
    import application.models.servers as serverModel
    from application import redisModel
    fresh, stale, never = servers["bg-alice@test.local"][2][0], servers["bg-alice@test.local"][2][1], servers["bg-bob@test.local"][2][0]
    now = int(time.time())
    for server in (fresh, stale, never):
        redisModel.redisClient.delete(f"server-info:{server.uuid}", f"server-status:{server.uuid}")
    redisModel.saveServerInfo(fresh.uuid, {"timestamp": now - 60, "query_result": {}})
    redisModel.saveServerInfo(stale.uuid, {"timestamp": now - 1800, "query_result": {}})
    redisModel.saveServerStatus(fresh.uuid, {"version": "2.5.1", "timestamp": now - 60})
    redisModel.saveServerStatus(stale.uuid, {"version": "2.5.1", "timestamp": now - 290})  # Within the slack

    assert serverModel.serversDueForRefresh([fresh, stale, never], 1800, now) == [stale, never]
    assert serverModel.serversDueForConnectionTest([fresh, stale, never], 300, now) == [stale, never]


def test_background_connection_test(monkeypatch, servers, emitted, bg_settings):
    """Every due server of every user is tested; each result goes to its owner only and is persisted"""
    import application.models.servers as serverModel
    import application.workers.tasks as tasks
    from application import redisModel
    alice, _, (aliceServer, noKeyServer) = servers["bg-alice@test.local"]
    bob, _, (bobServer,) = servers["bg-bob@test.local"]
    for server in (aliceServer, noKeyServer, bobServer):
        redisModel.redisClient.delete(f"server-status:{server.uuid}")
    fetched = {}

    async def fakeFetcher(serversToTest, url, callback, timeout=300, max_concurrency=None):
        fetched.update({"servers": [s.id for s in serversToTest], "timeout": timeout, "max_concurrency": max_concurrency})
        for server in serversToTest:
            callback(server.id, {"version": "2.5.1", "_latency": 0.1, "_status_code": 200})
    monkeypatch.setattr(serverModel, "asyncFetcherManyServer", fakeFetcher)

    tasks.backgroundConnectionTest.call_local()

    ours = {aliceServer.id, noKeyServer.id, bobServer.id}
    assert ours & set(fetched["servers"]) == {aliceServer.id, bobServer.id}  # No request without an API key
    assert fetched["max_concurrency"] == 2 and fetched["timeout"] == tasks.BACKGROUND_CONNECTION_TEST_TIMEOUT
    assert redisModel.getServerStatus(aliceServer.uuid)["version"] == "2.5.1"
    assert redisModel.getServerStatus(noKeyServer.uuid)["error"] == "No API key configured"
    updates = {data["server"]["id"]: room for event, data, room in emitted if event == "UPDATE_SERVER_CONNECTION"}
    assert updates[aliceServer.id] == f"user:{alice.id}"
    assert updates[noKeyServer.id] == f"user:{alice.id}"
    assert updates[bobServer.id] == f"user:{bob.id}"

    # Nothing is due right after a run
    fetched.clear()
    tasks.backgroundConnectionTest.call_local()
    assert not (ours & set(fetched.get("servers", [])))


def test_background_full_refresh(monkeypatch, servers, emitted, bg_settings):
    import application.models.servers as serverModel
    import application.workers.tasks as tasks
    from application import redisModel
    aliceServer, noKeyServer = servers["bg-alice@test.local"][2]
    bobServer = servers["bg-bob@test.local"][2][0]
    now = int(time.time())
    redisModel.saveServerInfo(aliceServer.uuid, {"timestamp": now - 3600, "query_result": {}})
    redisModel.saveServerInfo(bobServer.uuid, {"timestamp": now - 60, "query_result": {}})  # Watched: fresh
    refreshed = []

    async def fakeFetch(server, callbacks):
        refreshed.append(server.id)
        if server.id == aliceServer.id:
            raise RuntimeError("MISP returned garbage")  # Must not stop the other refreshes
        return {}
    monkeypatch.setattr(serverModel, "fetchServerInfoAsync", fakeFetch)

    tasks.backgroundFullRefresh.call_local()

    ours = {aliceServer.id, noKeyServer.id, bobServer.id}
    assert ours & set(refreshed) == {aliceServer.id}


def test_background_refresh_can_be_disabled(monkeypatch, servers, bg_settings):
    import application.models.servers as serverModel
    import application.workers.tasks as tasks
    bg_settings["enabled"] = False
    monkeypatch.setattr(serverModel, "serversDueForConnectionTest", lambda *a: pytest.fail("should not run"))
    monkeypatch.setattr(serverModel, "serversDueForRefresh", lambda *a: pytest.fail("should not run"))

    tasks.backgroundConnectionTest.call_local()
    tasks.backgroundFullRefresh.call_local()


def test_background_run_is_skipped_while_the_previous_one_runs(monkeypatch, servers, bg_settings):
    import application.models.servers as serverModel
    import application.workers.tasks as tasks
    from application import redisModel
    monkeypatch.setattr(serverModel, "serversDueForConnectionTest", lambda *a: pytest.fail("should not run"))
    redisModel.redisClient.set("background-connection-test-lock", "another-run", ex=60)
    try:
        assert tasks.backgroundConnectionTest.call_local() is None
    finally:
        redisModel.redisClient.delete("background-connection-test-lock")
    assert redisModel.redisClient.get("background-connection-test-lock") is None


def test_background_settings_defaults():
    import application.models.setting as settingModel
    import application.workers.tasks as tasks
    defaults = {name: settingModel.get(name)["default"] for name in (
        "health_background_refresh_enabled", "health_connection_test_interval",
        "health_full_refresh_interval", "health_max_concurrency")}
    assert defaults == {"health_background_refresh_enabled": True, "health_connection_test_interval": 5,
                        "health_full_refresh_interval": 30, "health_max_concurrency": 10}
    config = tasks.backgroundRefreshSettings()
    assert set(config) == {"enabled", "connection_test_interval", "full_refresh_interval", "max_concurrency"}


@pytest.mark.parametrize("name, value, status", [
    ("health_connection_test_interval", 0, 400),
    ("health_connection_test_interval", "abc", 400),
    ("health_connection_test_interval", 2.5, 400),
    ("health_connection_test_interval", True, 400),
    ("health_full_refresh_interval", 100000, 400),
    ("health_background_refresh_enabled", "yes", 400),
    ("fleet_watching_interval", 5, 400),  # Not configurable
    ("no_such_setting", 1, 404),
])
def test_setting_values_are_validated(client, auth_headers, make_user, name, value, status):
    admin = make_user("bg-admin@test.local", is_admin=True)
    response = client.post(f"/instance/settings/edit/{name}", json={"value": value}, headers=auth_headers(admin))
    assert response.status_code == status
    assert response.json["message"]


def test_valid_setting_value_is_normalised(monkeypatch, client, auth_headers, make_user):
    import application.models.setting as settingModel
    saved = {}
    monkeypatch.setattr(settingModel, "set", lambda name, value: saved.update({name: value}) or {"value": value})
    admin = make_user("bg-admin@test.local", is_admin=True)

    response = client.post("/instance/settings/edit/health_connection_test_interval", json={"value": "10"},
                           headers=auth_headers(admin))

    assert response.status_code == 200
    assert saved == {"health_connection_test_interval": 10}
