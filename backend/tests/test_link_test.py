"""Link test: re-testing sync links without a full refresh, for a fleet, a server or a single link"""
import asyncio
import copy
import json
from pathlib import Path

import pytest

SNAPSHOT = json.loads((Path(__file__).parent / "fixtures" / "snapshot_misp_3.0.0.json").read_text())
SNAPSHOT.pop("_fixture", None)
OK = {"status": 1, "version": "3.0.0", "local_version": "3.0.0", "mismatch": False, "newer": False, "post": 1}
SYNC_USER = {"User": "sync@remote.test", "Role name": "Sync user", "Sync flag": "Yes"}


@pytest.fixture(autouse=True)
def _latest_release(app, monkeypatch):
    import application.health.versions as versions
    monkeypatch.setattr(versions, "latest_release", lambda *args, **kwargs: "v3.0.0")


def remote(remote_id, push=True, pull=True):
    return {"Server": {"id": str(remote_id), "name": f"Remote {remote_id}", "url": f"https://r{remote_id}.test",
                       "push": push, "pull": pull, "authkey": "must-not-be-kept"}}


@pytest.fixture()
def owned(db, make_user):
    """alice owns `hub` (with a snapshot whose links were all tested OK) and `fresh` (never refreshed)"""
    from application import redisModel
    from application.DBModels import Fleet, Server
    from application.models.servers import parseMISPConnectionOutput, parseMISPUserConnectionOutput
    alice = make_user("linktest-alice@test.local")
    fleet = Fleet(name="Links", description="", user_id=alice.id, timestamp=1)
    db.session.add(fleet)
    db.session.commit()
    servers = {}
    for name in ("hub", "fresh"):
        servers[name] = Server(name=name, url=f"https://{name}.test", authkey="k" * 40, fleet_id=fleet.id,
                               user_id=alice.id)
        db.session.add(servers[name])
    db.session.commit()
    snapshot = copy.deepcopy(SNAPSHOT)
    snapshot["timestamp"] = 1_700_000_000
    snapshot["query_result"]["connectedServers"] = [
        {**remote(i), "connectionTest": parseMISPConnectionOutput({**OK, "timestamp": 1_700_000_000}),
         "connectionUser": parseMISPUserConnectionOutput(SYNC_USER), "vid": f"{servers['hub'].id}-{i}"}
        for i in (1, 2, 3)]
    for link in snapshot["query_result"]["connectedServers"]:
        link["Server"].pop("authkey")
    redisModel.saveServerInfo(servers["hub"].uuid, snapshot)
    redisModel.redisClient.delete(f"server-info:{servers['fresh'].uuid}")
    yield alice, fleet, servers
    for server in servers.values():
        redisModel.redisClient.delete(f"link-test-lock:{server.id}")
        db.session.delete(server)
    db.session.commit()
    db.session.delete(fleet)
    db.session.commit()


@pytest.fixture()
def misp(monkeypatch):
    """A fake MISP answering by URL. `answers` can be changed by tests; `fetched` lists the requested URLs"""
    import application.models.servers as serverModel
    state = {
        "answers": {"/servers/index": [remote(1), remote(2), remote(3)]},
        "tests": {"1": {"status": 4}, "2": OK, "3": {**OK, "post": 8}},
        "fetched": [], "inflight": 0, "max_inflight": 0,
    }

    async def fakeFetcher(server, urls, timeout=300):
        results = []
        for url in urls:
            state["fetched"].append(url)
            state["inflight"] += 1
            state["max_inflight"] = max(state["max_inflight"], state["inflight"])
            await asyncio.sleep(0.01)
            state["inflight"] -= 1
            if url.startswith("/servers/testConnection/"):
                answer = state["tests"][url.rsplit("/", 1)[1]]
                if isinstance(answer, Exception):
                    raise answer
                results.append(copy.deepcopy(answer))
            elif url.startswith("/servers/getRemoteUser/"):
                results.append(copy.deepcopy(SYNC_USER))
            else:
                results.append(copy.deepcopy(state["answers"].get(url, {"error": f"unexpected {url}"})))
        return results
    monkeypatch.setattr(serverModel, "asyncFetcher", fakeFetcher)
    return state


@pytest.fixture()
def emitted(monkeypatch):
    """Events from the workers and from the web process (health updates)"""
    import application.workers.tasks as tasks
    from application.controllers.websocket import socketEmitter
    events = []
    for emitter in (tasks.socketioEmitter, socketEmitter):
        monkeypatch.setattr(emitter.socketio, "emit",
                            lambda event, data=None, **kw: events.append((event, data, kw.get("to"))))
    return events


def links(server):
    from application import redisModel
    return {link["Server"]["id"]: link for link in redisModel.getServerInfo(server.uuid)["query_result"]["connectedServers"]}


def levels(server):
    from application.health.links import classify_link
    return {remote_id: classify_link(link)["level"] for remote_id, link in links(server).items()}


def run(servers, **kwargs):
    import application.models.servers as serverModel
    done = []
    updates = []
    callbacks = {"link_test_done": lambda server, result: done.append((server.id, result)),
                 "udpate_server_connection_list": lambda server, data: updates.append((server.id, len(data)))}
    serverModel.testLinks(servers, callbacks, **kwargs)
    return done, updates


# --- Model ------------------------------------------------------------------------------------------------------------

def test_links_are_tested_without_a_full_refresh(owned, misp, emitted):
    from application import redisModel
    alice, fleet, servers = owned
    hub = servers["hub"]
    before = redisModel.getServerInfo(hub.uuid)

    done, updates = run([hub])

    assert done == [(hub.id, {"tested": 3})] and updates == [(hub.id, 3)]
    assert levels(hub) == {"1": "broken", "2": "ok", "3": "broken"}
    assert all(not url.startswith(("/servers/serverSettings", "/users/")) for url in misp["fetched"])
    after = redisModel.getServerInfo(hub.uuid)
    assert after["timestamp"] == before["timestamp"]  # Only the links changed: the snapshot is not "refreshed"
    assert after["query_result"]["serverSettings"] == before["query_result"]["serverSettings"]
    assert all("authkey" not in link["Server"] for link in links(hub).values())
    health = [data for event, data, room in emitted if event == "HEALTH_UPDATED"]
    assert len(health) == 1 and health[0]["server_id"] == hub.id
    assert {i["subject"] for i in health[0]["issues"] if i["rule"] == "sync_link"} == {"1", "3"}


def test_links_of_a_server_are_tested_a_few_at_a_time(owned, misp):
    import application.models.servers as serverModel
    hub = owned[2]["hub"]
    misp["answers"]["/servers/index"] = [remote(i) for i in range(1, 11)]
    misp["tests"] = {str(i): OK for i in range(1, 11)}
    run([hub])
    assert 1 < misp["max_inflight"] <= serverModel.LINK_TEST_CONCURRENCY


def test_one_failing_link_does_not_stop_the_others(owned, misp):
    hub = owned[2]["hub"]
    misp["tests"]["1"] = RuntimeError("boom")
    done, _ = run([hub])
    assert done == [(hub.id, {"tested": 3})]
    assert links(hub)["1"]["connectionTest"]["test_error"].startswith("Unhandled Exception")
    assert levels(hub) == {"1": "unknown", "2": "ok", "3": "broken"}


def test_a_single_link_can_be_tested(owned, misp):
    hub = owned[2]["hub"]
    previous = links(hub)
    done, _ = run([hub], remote_server_id=3)
    assert done == [(hub.id, {"tested": 1})]
    assert [url for url in misp["fetched"] if "testConnection" in url] == ["/servers/testConnection/3"]
    assert levels(hub) == {"1": "ok", "2": "ok", "3": "broken"}  # 1 and 2 keep their last result
    assert links(hub)["1"]["connectionTest"] == previous["1"]["connectionTest"]


def test_testing_an_unknown_link_changes_nothing(owned, misp):
    hub = owned[2]["hub"]
    previous = links(hub)
    done, updates = run([hub], remote_server_id=42)
    assert done == [(hub.id, {"error": "No sync connection with ID 42"})] and updates == []
    assert links(hub) == previous


@pytest.mark.parametrize("answer, error", [
    ({"error": "Timeout Exception (30s)"}, "Could not list the sync connections: Timeout Exception (30s)"),
    ({"_status_code": 403, "name": "Forbidden"}, "Could not list the sync connections: Forbidden"),
])
def test_last_known_links_are_kept_when_they_cannot_be_listed(owned, misp, emitted, answer, error):
    hub = owned[2]["hub"]
    previous = links(hub)
    misp["answers"]["/servers/index"] = answer
    done, updates = run([hub])
    assert done == [(hub.id, {"error": error})] and updates == []
    assert links(hub) == previous
    assert not any(url.startswith("/servers/testConnection") for url in misp["fetched"])


def test_a_server_without_data_gets_a_full_refresh(monkeypatch, owned, misp):
    import application.models.servers as serverModel
    fresh = owned[2]["fresh"]
    refreshed = []

    async def fakeFullRefresh(server, callbacks):
        refreshed.append(server.id)
    monkeypatch.setattr(serverModel, "fetchServerInfoAsync", fakeFullRefresh)
    done, _ = run([fresh])
    assert refreshed == [fresh.id] and done == [(fresh.id, {"full_refresh": True})]


def test_a_server_without_api_key_is_not_queried(db, owned, misp):
    hub = owned[2]["hub"]
    hub.authkey = None
    db.session.commit()
    done, _ = run([hub])
    assert done == [(hub.id, {"error": "No API key configured"})] and misp["fetched"] == []


# --- Task -------------------------------------------------------------------------------------------------------------

def linkTestEvents(events):
    return [(data, room) for event, data, room in events if event == "SERVER_LINK_TEST"]


def test_task_reports_progress_to_the_owner(owned, misp, emitted):
    import application.workers.tasks as tasks
    from application import redisModel
    alice, fleet, servers = owned
    hub = servers["hub"]
    tasks.doLinkTestTask.call_local([hub.id])
    room = f"user:{alice.id}"
    assert linkTestEvents(emitted) == [({"server_id": hub.id, "testing": True}, room),
                                       ({"server_id": hub.id, "testing": False}, room)]
    partial = [data for event, data, _ in emitted if event == "UPDATE_SERVER_PARTIAL_DATA"]
    assert [(p["server_id"], p["partial_data_key"]) for p in partial] == [(hub.id, "connectedServers")]
    assert redisModel.redisClient.get(f"link-test-lock:{hub.id}") is None


def test_task_reports_errors(owned, misp, emitted):
    import application.workers.tasks as tasks
    hub = owned[2]["hub"]
    misp["answers"]["/servers/index"] = {"error": "Connection Error: refused"}
    tasks.doLinkTestTask.call_local([hub.id])
    assert linkTestEvents(emitted)[-1][0] == {
        "server_id": hub.id, "testing": False, "error": "Could not list the sync connections: Connection Error: refused"}


def test_a_server_already_being_tested_is_skipped(owned, misp, emitted):
    import application.workers.tasks as tasks
    from application import redisModel
    hub = owned[2]["hub"]
    redisModel.redisClient.set(f"link-test-lock:{hub.id}", "another-run", ex=60)
    tasks.doLinkTestTask.call_local([hub.id])
    assert misp["fetched"] == [] and linkTestEvents(emitted) == []
    assert redisModel.redisClient.get(f"link-test-lock:{hub.id}") == "another-run"  # Not ours to release


def test_task_releases_its_locks_when_the_run_fails(monkeypatch, owned, misp, emitted):
    import application.models.servers as serverModel
    import application.workers.tasks as tasks
    from application import redisModel
    hub = owned[2]["hub"]
    monkeypatch.setattr(serverModel, "testLinks", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("loop died")))
    with pytest.raises(RuntimeError):
        tasks.doLinkTestTask.call_local([hub.id])
    assert redisModel.redisClient.get(f"link-test-lock:{hub.id}") is None
    assert linkTestEvents(emitted)[-1][0] == {"server_id": hub.id, "testing": False,
                                             "error": "The link test failed unexpectedly"}


def test_fleet_link_test_is_faster_than_a_full_refresh(owned, misp):
    """A link test makes fewer requests than a full refresh: no diagnostics, user, registrations, usage or
    organisations (listed by the refresh when the fleet has other servers to compare them with)"""
    import application.models.servers as serverModel
    hub = owned[2]["hub"]
    run([hub])
    linkTestRequests = list(misp["fetched"])
    misp["fetched"].clear()
    misp["answers"].update({"/servers/serverSettings/diagnostics/light:1": {}, "/users/view/me": {},
                            "/users/registrations": [], "/users/statistics": {}})
    asyncio.run(serverModel.fetchServerInfoAsync(hub, {}))
    assert set(misp["fetched"]) - set(linkTestRequests) == {
        "/servers/serverSettings/diagnostics/light:1", "/users/view/me", "/users/registrations", "/users/statistics",
        "/organisations/index/scope:all"}
