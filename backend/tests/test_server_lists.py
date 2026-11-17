"""Lists of servers carry a light snapshot; the server page asks for the full one; socket events and search results
name servers without their snapshot"""

import copy
import json
from pathlib import Path
import uuid

import pytest

SNAPSHOT = json.loads((Path(__file__).parent / "fixtures" / "snapshot_misp_3.0.0.json").read_text())
SNAPSHOT.pop("_fixture", None)
SETTINGS = SNAPSHOT["query_result"]["serverSettings"]


@pytest.fixture()
def listed(db, make_user):
    """A user with one server whose snapshot is a real MISP 3.0 one, plus a baseline content listing"""
    from application import redisModel
    from application.DBModels import Fleet, Server

    tag = uuid.uuid4().hex[:8]
    user = make_user(f"lists-{tag}@test.local")
    fleet = Fleet(name=f"Lists fleet {tag}", description="", user_id=user.id, timestamp=1)
    db.session.add(fleet)
    db.session.commit()
    server = Server(name=f"listed-misp-{tag}", url="https://listed.test", authkey="k" * 40, fleet_id=fleet.id, user_id=user.id)
    db.session.add(server)
    db.session.commit()
    snapshot = copy.deepcopy(SNAPSHOT)
    snapshot["query_result"]["baselineState"] = {"timestamp": 1, "taxonomies": {"items": {"tlp": {"enabled": True}}}}
    redisModel.saveServerInfo(server.uuid, snapshot)
    return user, fleet, server, snapshot


def test_fleet_list_carries_what_lists_show(client, auth_headers, listed):
    user, fleet, server, snapshot = listed
    response = client.get(f"/servers/index/{fleet.id}", headers=auth_headers(user))
    assert response.status_code == 200
    info = response.get_json()[0]["server_info"]
    full = snapshot["query_result"]
    assert info["light"] is True and info["timestamp"] == snapshot["timestamp"]
    assert set(info["query_result"]) == {"serverSettings", "serverUsage", "serverUser", "connectedServers"}
    for section in ("serverUsage", "serverUser", "connectedServers"):
        assert info["query_result"][section] == full[section]
    settings = info["query_result"]["serverSettings"]
    for part in ("version", "proxyStatus", "zmqStatus", "moduleStatus", "workers", "backgroundJobsStatus"):
        assert settings[part] == SETTINGS[part]
    assert not {"dbDiagnostics", "dbSchemaDiagnostics", "redisInfo", "phpSettings", "extensions"} & set(settings)
    assert {entry["setting"] for entry in settings["finalSettings"]} == {"MISP.uuid", "MISP.background_jobs"}
    assert len(json.dumps(info)) * 10 < len(json.dumps(snapshot))


def test_server_page_gets_the_full_snapshot(client, auth_headers, listed):
    user, _, server, snapshot = listed
    response = client.get(f"/servers/queryInfo/{server.id}", headers=auth_headers(user))
    assert response.status_code == 200
    data = response.get_json()
    assert "light" not in data
    assert data["query_result"]["serverSettings"]["finalSettings"] == SETTINGS["finalSettings"]
    assert data["query_result"]["serverSettings"]["dbDiagnostics"] == SETTINGS["dbDiagnostics"]


def test_settings_holding_an_error_stay_an_error():
    from application.marshmallowSchemas import lightServerInfo

    failed = {"timestamp": 5, "query_result": {"serverSettings": {"error": "Timeout", "_status_code": 504}}}
    assert lightServerInfo(failed)["query_result"]["serverSettings"] == {"error": "Timeout", "_status_code": 504}
    assert lightServerInfo({"error": "Unknown server"}) == {"error": "Unknown server"}
    assert lightServerInfo(None) is None


def test_refresh_event_carries_the_light_snapshot(monkeypatch, listed):
    from application.controllers.websocket import socketEmitter

    _, _, server, snapshot = listed
    events = []
    monkeypatch.setattr(socketEmitter.socketio, "emit", lambda event, data=None, **kw: events.append((event, data)))
    refreshed = dict(copy.deepcopy(snapshot), server={"id": server.id})
    socketEmitter.udpate_server(server, refreshed)
    [(event, update)] = events
    assert event == "UPDATE_SERVER" and update["light"] is True and update["server"] == {"id": server.id}
    finalSettings = update["query_result"]["serverSettings"]["finalSettings"]
    assert {entry["setting"] for entry in finalSettings} == {"MISP.uuid", "MISP.background_jobs"}
    # What the refresh saved is left whole
    assert len(refreshed["query_result"]["serverSettings"]["finalSettings"]) == len(SETTINGS["finalSettings"])
