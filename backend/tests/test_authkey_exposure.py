"""MISP authkeys must never be sent to clients, neither over REST nor over socket.io"""
import pytest

AUTHKEY = "A" * 36 + "k3y9"


def find_authkeys(payload, path="$"):
    """Paths of every `authkey` key, and of every value equal to the test authkey, in a JSON-like payload"""
    found = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == "authkey":
                found.append(f"{path}.{key}")
            found.extend(find_authkeys(value, f"{path}.{key}"))
    elif isinstance(payload, (list, tuple)):
        for i, value in enumerate(payload):
            found.extend(find_authkeys(value, f"{path}[{i}]"))
    elif payload == AUTHKEY:
        found.append(path)
    return found


@pytest.fixture()
def fleet_with_server(db, make_user):
    from application.DBModels import Fleet, Server
    from application import redisModel

    user = make_user("owner@test.local")
    fleet = Fleet(name="Fleet", description="", user_id=user.id, timestamp=1)
    db.session.add(fleet)
    db.session.commit()
    server = Server(name="misp1", url="https://misp1.test", authkey=AUTHKEY, fleet_id=fleet.id, user_id=user.id)
    db.session.add(server)
    db.session.commit()
    # A stored snapshot with one sync link (remote authkeys are stripped when fetched, see test_strip_remote_authkeys)
    redisModel.saveServerInfo(server.uuid, {
        "timestamp": 1,
        "query_result": {
            "connectedServers": [{
                "Server": {"id": "1", "name": "remote", "url": "https://remote.test", "pull": True, "push": False,
                           "pull_rules": "[]", "push_rules": "[]"},
            }],
        },
    })
    yield user, fleet, server
    db.session.delete(server)
    db.session.delete(fleet)
    db.session.commit()


def test_server_schemas_never_dump_authkey(fleet_with_server):
    from application.marshmallowSchemas import (ServerSchema, FleetSchema, serverSchema, serversSchema,
                                                serverSchemaLighter, serversSchemaLighter, fleetSchema, fleetsSchema)
    _, fleet, server = fleet_with_server
    dumps = {
        "serverSchema": serverSchema.dump(server),
        "serversSchema": serversSchema.dump([server]),
        "serverSchemaLighter": serverSchemaLighter.dump(server),
        "serversSchemaLighter": serversSchemaLighter.dump([server]),
        "ServerSchema(exclude)": ServerSchema(exclude=("server_info",)).dump(server),
        "fleetSchema": fleetSchema.dump(fleet),
        "fleetsSchema": fleetsSchema.dump([fleet]),
        "FleetSchema(exclude)": FleetSchema(exclude=("servers",)).dump(fleet),
    }
    for name, dump in dumps.items():
        assert find_authkeys(dump) == [], name

    dumped = serverSchema.dump(server)
    assert dumped["authkey_hint"] == "••••k3y9"
    assert dumped["has_authkey"] is True
    assert fleetSchema.dump(fleet)["servers"][0]["authkey_hint"] == "••••k3y9"


def test_server_schema_still_loads_authkey(app):
    from application.marshmallowSchemas import ServerSchema
    loaded = ServerSchema(only=("authkey",), load_instance=False).load({"authkey": AUTHKEY})
    assert loaded["authkey"] == AUTHKEY


def test_strip_remote_authkeys():
    from application.models.servers import stripRemoteAuthkeys
    index = [{"Server": {"id": "1", "authkey": AUTHKEY}}, {"Server": {"id": "2"}}, "garbage"]
    assert find_authkeys(stripRemoteAuthkeys(index)) == []
    assert stripRemoteAuthkeys({"error": "Server unreachable"}) == {"error": "Server unreachable"}


@pytest.mark.parametrize("method,url_fn,body_fn", [
    ("get", lambda f, s: f"/servers/index/{f.id}", None),
    ("get", lambda f, s: f"/servers/get/{s.id}", None),
    ("get", lambda f, s: "/fleets/index", None),
    ("get", lambda f, s: f"/fleets/get/{f.id}", None),
    ("get", lambda f, s: "/instance/searchAll/misp", None),
    ("get", lambda f, s: f"/servers/network/{f.id}", None),
    ("get", lambda f, s: f"/servers/getConnection/{s.id}/1", None),
    ("post", lambda f, s: "/servers/edit", lambda f, s: {"id": s.id, "comment": "edited"}),
])
def test_routes_never_return_authkey(client, auth_headers, fleet_with_server, method, url_fn, body_fn):
    user, fleet, server = fleet_with_server
    kwargs = {"headers": auth_headers(user)}
    if body_fn is not None:
        kwargs["json"] = body_fn(fleet, server)
    response = getattr(client, method)(url_fn(fleet, server), **kwargs)
    assert response.status_code == 200, response.data
    payload = response.get_json()
    assert payload, "the route returned nothing, so the check proves nothing"
    assert find_authkeys(payload) == []


def test_add_returns_hint_not_key(client, auth_headers, fleet_with_server, db):
    from application.DBModels import Server
    user, fleet, _ = fleet_with_server
    response = client.post(f"/servers/add/{fleet.id}", headers=auth_headers(user),
                           json={"name": "misp2", "url": "https://misp2.test", "authkey": AUTHKEY})
    payload = response.get_json()
    assert find_authkeys(payload) == []
    assert payload["authkey_hint"] == "••••k3y9"
    created = db.session.get(Server, payload["id"])
    assert created.authkey == AUTHKEY
    db.session.delete(created)
    db.session.commit()


def test_edit_with_empty_authkey_keeps_current_key(client, auth_headers, fleet_with_server, db):
    from application.DBModels import Server
    user, _, server = fleet_with_server
    headers = auth_headers(user)

    client.post("/servers/edit", headers=headers, json={"id": server.id, "name": "renamed", "authkey": ""})
    db.session.expire_all()
    assert db.session.get(Server, server.id).authkey == AUTHKEY

    newKey = "B" * 40
    client.post("/servers/edit", headers=headers, json={"id": server.id, "authkey": newKey})
    db.session.expire_all()
    assert db.session.get(Server, server.id).authkey == newKey


def test_socket_emits_never_contain_authkey(monkeypatch, fleet_with_server):
    from application.controllers.websocket import SocketioEmitter
    _, _, server = fleet_with_server
    emitter = SocketioEmitter()
    emitted = []
    monkeypatch.setattr(emitter.socketio, "emit", lambda event, data=None, **kw: emitted.append((event, data)))

    emitter.udpate_server_connection_list(server, [{"Server": {"id": "1"}}])
    emitter.udpate_server_usage(server, {})
    emitter.server_graphs_update_done(server.id, 1)

    assert {event for event, _ in emitted} >= {"UPDATE_SERVER_PARTIAL_DATA", "SERVER_GRAPHS_UPDATE_DONE"}
    for event, data in emitted:
        assert find_authkeys(data) == [], event


def test_tasks_take_server_ids(monkeypatch, fleet_with_server):
    """Tasks are queued with IDs; their socket payloads must not contain the authkey either"""
    import application.workers.tasks as tasks
    import application.models.servers as serverModel
    _, _, server = fleet_with_server
    emitted = []
    monkeypatch.setattr(tasks.socketioEmitter.socketio, "emit", lambda event, data=None, **kw: emitted.append((event, data)))
    monkeypatch.setattr(serverModel, "testConnectionAsync", lambda server_id: {"status": 0})

    tasks.doServerConnectionTestTask.call_local(server.id)

    updates = [data for event, data in emitted if event == "UPDATE_SERVER_CONNECTION"]
    assert updates and updates[0]["server"]["id"] == server.id
    assert find_authkeys(emitted) == []
