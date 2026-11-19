"""socket.io: connections need a valid token, users only get events about their own resources and can't act
on resources of other users"""
import pytest


@pytest.fixture()
def two_users(db, make_user):
    from application.DBModels import Fleet, Server
    users = {}
    created = []
    for name in ("alice", "bob"):
        user = make_user(f"{name}@test.local")
        fleet = Fleet(name=f"{name} fleet", description="", user_id=user.id, timestamp=1)
        db.session.add(fleet)
        db.session.commit()
        server = Server(name=f"{name}-misp", url=f"https://{name}.test", authkey="K" * 40, fleet_id=fleet.id, user_id=user.id)
        db.session.add(server)
        db.session.commit()
        users[name] = (user, fleet, server)
        created += [server, fleet]
    yield users
    for model in created:
        db.session.delete(model)
    db.session.commit()


@pytest.fixture()
def queued(monkeypatch):
    """Record the tasks the socket handlers queue instead of sending them to the workers"""
    import application.workers.tasks as tasks
    calls = []
    for name in ("fetchServerInfoTask", "doFleetInfoTask", "doServerConnectionTestTask",
                 "doFleetConnectionTestTask"):
        monkeypatch.setattr(tasks, name, lambda arg, _name=name: calls.append((_name, arg)))
    return calls


def test_connection_refused_without_valid_token(socket_client, two_users):
    assert not socket_client().is_connected()
    assert not socket_client(token="not-a-jwt").is_connected()
    assert not socket_client(token="Apikey unknown-key").is_connected()


def test_connection_accepted_with_jwt_or_apikey(socket_client, two_users, db):
    alice, _, _ = two_users["alice"]
    assert socket_client(user=alice).is_connected()
    alice.setAPIKey("A" * 40)
    db.session.commit()
    assert socket_client(token=f"Apikey {'A' * 40}").is_connected()


def test_cannot_act_on_resources_of_another_user(socket_client, two_users, queued):
    alice, aliceFleet, aliceServer = two_users["alice"]
    bob, bobFleet, bobServer = two_users["bob"]
    bobClient = socket_client(user=bob)

    for event, target in [("refresh_server", aliceServer.id), ("server_connection_test", aliceServer.id),
                          ("refresh_fleet", aliceFleet.id), ("fleet_connection_test", aliceFleet.id)]:
        bobClient.emit(event, target)
    assert queued == []

    bobClient.emit("refresh_server", bobServer.id)
    bobClient.emit("refresh_fleet", bobFleet.id)
    assert queued == [("fetchServerInfoTask", bobServer.id), ("doFleetInfoTask", [bobServer.id])]


def test_events_only_reach_the_owner(monkeypatch, app, socket_client, two_users):
    from application import socketioApp
    from application.controllers.websocket import SocketioEmitter
    alice, aliceFleet, aliceServer = two_users["alice"]
    bob, _, _ = two_users["bob"]
    aliceClient = socket_client(user=alice)
    bobClient = socket_client(user=bob)

    emitter = SocketioEmitter()
    emitter.socketio = socketioApp  # Emit through the app's in-memory server, where the test clients are
    emitter.server_updating(aliceServer)
    emitter.udpate_server_connection(aliceServer, {"status": 0})
    emitter.udpate_server(aliceServer.id, {"timestamp": 1})
    emitter.fleet_update_timestamps(aliceFleet.id, watched_timestamp=1)

    aliceEvents = [event["name"] for event in aliceClient.get_received()]
    assert aliceEvents == ["SERVER_UPDATING", "UPDATE_SERVER_CONNECTION", "UPDATE_SERVER", "FLEET_UPDATE_TIMESTAMPS"]
    assert bobClient.get_received() == []


def test_events_about_unknown_servers_are_dropped(monkeypatch, socket_client, two_users):
    from application.controllers.websocket import SocketioEmitter
    emitter = SocketioEmitter()
    emitted = []
    monkeypatch.setattr(emitter.socketio, "emit", lambda *args, **kwargs: emitted.append((args, kwargs)))
    emitter.server_updating(999999)
    emitter.fleet_update_timestamps(999999, watched_timestamp=1)
    assert emitted == []


def test_pong_only_goes_to_the_asking_socket(monkeypatch, socket_client, two_users):
    from application import socketioApp
    import application.workers.tasks as tasks
    alice, _, _ = two_users["alice"]
    bob, _, _ = two_users["bob"]
    aliceClient = socket_client(user=alice)
    bobClient = socket_client(user=bob)
    monkeypatch.setattr(tasks.socketioEmitter, "socketio", socketioApp)

    aliceSid = socketioApp.server.manager.sid_from_eio_sid(aliceClient.eio_sid, "/")
    tasks.ping.call_local(aliceSid)

    assert [event["name"] for event in aliceClient.get_received()] == ["PONG"]
    assert bobClient.get_received() == []


def test_link_tests_only_for_ones_own_servers(monkeypatch, socket_client, two_users):
    import application.workers.tasks as tasks
    calls = []
    monkeypatch.setattr(tasks, "doLinkTestTask",
                        lambda server_ids, remote_server_id=None: calls.append((server_ids, remote_server_id)))
    alice, aliceFleet, aliceServer = two_users["alice"]
    bob, bobFleet, bobServer = two_users["bob"]
    bobClient = socket_client(user=bob)

    bobClient.emit("fleet_link_test", aliceFleet.id)
    bobClient.emit("server_link_test", aliceServer.id)
    bobClient.emit("server_link_test", {"server_id": aliceServer.id, "remote_server_id": 3})
    bobClient.emit("server_link_test", {"server_id": bobServer.id, "remote_server_id": "3; drop"})
    assert calls == []

    bobClient.emit("fleet_link_test", bobFleet.id)
    bobClient.emit("server_link_test", bobServer.id)
    bobClient.emit("server_link_test", {"server_id": bobServer.id, "remote_server_id": "3"})
    assert calls == [([bobServer.id], None), ([bobServer.id], None), ([bobServer.id], 3)]
