"""Socket events and search results name servers without their snapshot (several hundred KB each)"""

import json
import uuid

import pytest


@pytest.fixture()
def named(db, make_user):
    from application import redisModel
    from application.DBModels import Fleet, Server

    tag = uuid.uuid4().hex[:8]
    user = make_user(f"events-{tag}@test.local")
    fleet = Fleet(name=f"Events fleet {tag}", description="", user_id=user.id, timestamp=1)
    db.session.add(fleet)
    db.session.commit()
    server = Server(name=f"named-misp-{tag}", url="https://named.test", authkey="k" * 40, fleet_id=fleet.id, user_id=user.id)
    db.session.add(server)
    db.session.commit()
    finalSettings = [{"setting": f"MISP.setting_{n}", "value": n} for n in range(2000)]
    redisModel.saveServerInfo(server.uuid, {"timestamp": 1, "query_result": {"serverSettings": {"finalSettings": finalSettings}}})
    return user, fleet, server


def test_search_results_have_no_snapshot(client, auth_headers, named):
    user, fleet, server = named
    response = client.get(f"/instance/searchAll/{server.name}", headers=auth_headers(user))
    assert response.status_code == 200
    [found] = response.get_json()
    assert found["id"] == server.id and found["fleet"]["name"] == fleet.name and found["url"] == server.url
    assert "server_info" not in found


def test_partial_updates_name_the_server_without_its_snapshot(monkeypatch, named):
    from application.controllers.websocket import socketEmitter

    _, _, server = named
    events = []
    monkeypatch.setattr(socketEmitter.socketio, "emit", lambda event, data=None, **kw: events.append((event, data)))
    socketEmitter.udpate_server_connection_list(server, [])
    socketEmitter.udpate_server_usage(server, {"users": 1})
    assert [event for event, _ in events] == ["UPDATE_SERVER_PARTIAL_DATA"] * 2
    for _, data in events:
        assert "server_info" not in data["server"] and data["server"]["fleet"]["id"] == server.fleet_id
        assert len(json.dumps(data)) < 5000
