"""Logins over time, read from MISP 3's log index"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest


def logEntry(action, created, title="User (3): ana@org.test", ip="10.0.0.1", email="ana@org.test"):
    return {"Log": {"action": action, "created": created.strftime("%Y-%m-%d %H:%M:%S"), "title": title, "ip": ip,
                    "email": email, "model": "User"}}


def test_login_entries_are_parsed(app):
    from application.controllers.servers import parseGetLoginLogs
    now = datetime.now(timezone.utc).replace(microsecond=0)
    logins = parseGetLoginLogs([
        logEntry("login", now - timedelta(hours=1)),
        logEntry("auth_fail", now - timedelta(hours=2), title="Failed authentication using API key (abcd)"),
        logEntry("login", now - timedelta(days=9)),  # Too old
        logEntry("login", now, title="Unexpected title"),
        {"Log": {"action": "login", "created": "not a date"}},
        {"action": "edit", "created": now.isoformat()},
        "junk",
    ])
    assert logins["login"][0] == {"userid": 3, "email": "ana@org.test", "ip": "10.0.0.1",
                                  "created": int((now - timedelta(hours=1)).timestamp())}
    assert logins["login"][1]["userid"] is None and logins["login"][1]["email"] == "ana@org.test"
    assert len(logins["login"]) == 2
    assert logins["auth_fail"] == [{"userid": None, "email": None, "ip": "10.0.0.1",
                                    "created": int((now - timedelta(hours=2)).timestamp())}]


@pytest.fixture()
def server(db, make_user):
    from application.DBModels import Fleet, Server
    user = make_user(f"logins-{uuid.uuid4().hex[:8]}@test.test")
    fleet = Fleet(name="Logins", description="", user_id=user.id, timestamp=1)
    db.session.add(fleet)
    db.session.commit()
    theServer = Server(name="logins-misp", url="https://logins.test", user_id=user.id, fleet_id=fleet.id)
    db.session.add(theServer)
    db.session.commit()
    return user, theServer


def test_the_route_reads_the_log_index(server, client, auth_headers, monkeypatch):
    import application.controllers.servers as serverController
    user, theServer = server
    sent = []
    now = datetime.now(timezone.utc)

    def answer(srv, url, data, timeout=None, **kwargs):
        sent.append((url, data))
        return {"data": [logEntry("login", now - timedelta(minutes=5))], "_status_code": 200}
    monkeypatch.setattr(serverController, "mispPostRequest", answer)
    body = client.get(f"/servers/loginOvertime/{theServer.id}", headers=auth_headers(user)).get_json()
    assert sent[0][0] == "/admin/logs/index"
    assert sent[0][1]["model"] == "User" and sent[0][1]["action"] == ["login", "auth_fail"]
    assert sent[0][1]["created"] == "7d"
    assert body["data"]["login"][0]["email"] == "ana@org.test"

    monkeypatch.setattr(serverController, "mispPostRequest",
                        lambda *a, **k: {"name": "Forbidden", "_status_code": 403})
    body = client.get(f"/servers/loginOvertime/{theServer.id}", headers=auth_headers(user)).get_json()
    assert body == {"error": "MISP refused to list its logs: the API key needs admin rights"}
