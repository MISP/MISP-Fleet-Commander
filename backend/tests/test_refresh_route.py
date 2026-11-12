"""Queueing a full refresh over REST"""
import uuid
from types import SimpleNamespace


def test_queue_a_refresh(db, client, auth_headers, make_user, monkeypatch):
    from application.DBModels import Fleet, Server
    from application.workers import tasks
    user = make_user(f"refresh-{uuid.uuid4().hex[:8]}@test.test")
    fleet = Fleet(name="Refresh", description="", user_id=user.id, timestamp=1)
    db.session.add(fleet)
    db.session.commit()
    server = Server(name="refresh-misp", url="https://refresh.test", user_id=user.id, fleet_id=fleet.id)
    db.session.add(server)
    db.session.commit()
    queued = []
    monkeypatch.setattr(tasks, "fetchServerInfoTask",
                        lambda server_id: queued.append(server_id) or SimpleNamespace(id=str(uuid.uuid4())))

    response = client.get(f"/servers/queryInfoWS/{server.id}", headers=auth_headers(user))
    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.get_json()["status"] == "queued" and queued == [server.id]
