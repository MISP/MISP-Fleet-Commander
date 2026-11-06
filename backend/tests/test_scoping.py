"""Roles and scoping: users only reach their own resources; user management and instance settings are for admins"""
import pytest


@pytest.fixture()
def world(db, make_user):
    """alice and bob are regular users with a fleet, a server, a pinned entry and a setting each; root is an admin"""
    from application.DBModels import Fleet, Server, PinList, UserSettings
    created = []
    data = {"root": make_user("root@test.local", is_admin=True)}
    for name in ("alice", "bob"):
        user = make_user(f"{name}@test.local")
        fleet = Fleet(name=f"{name} fleet", description="", user_id=user.id, timestamp=1)
        db.session.add(fleet)
        db.session.commit()
        server = Server(name=f"{name}-misp", url=f"https://{name}.test", authkey="K" * 40, fleet_id=fleet.id, user_id=user.id)
        pin = PinList(model="Event", uuid=f"00000000-0000-0000-0000-00000000000{1 if name == 'alice' else 2}", user_id=user.id)
        setting = UserSettings(user_id=user.id, name="Plugins.enabled_plugins")
        setting.value = []
        db.session.add_all([server, pin, setting])
        db.session.commit()
        data[name] = {"user": user, "fleet": fleet, "server": server, "pin": pin, "setting": setting}
        created += [setting, pin, server, fleet]
    yield data
    for model in created:
        db.session.delete(model)
    db.session.commit()


@pytest.fixture()
def call(client, auth_headers):
    def _call(user, method, url, json=None):
        return getattr(client, method)(url, headers=auth_headers(user), json=json)
    return _call


def ids(world):
    a, b = world["alice"], world["bob"]
    return {"aServer": a["server"].id, "aFleet": a["fleet"].id, "aPin": a["pin"].id, "aSetting": a["setting"].id,
            "aUser": a["user"].id, "bPin": b["pin"].id, "root": world["root"].id}


ADMIN_ONLY = [
    ("get", "/users/index", None),
    ("get", "/users/get/{aUser}", None),
    ("post", "/users/add", {"email": "mallory@test.local", "password": "Password1234"}),
    ("post", "/users/delete/{aUser}", None),
    ("post", "/users/genAPIKey/{aUser}", None),
    ("get", "/users/view/{aUser}", None),
    ("post", "/users/edit", {"id": "{aUser}", "email": "pwned@test.local"}),
    ("post", "/instance/settings/edit/fleet_watching_enabled", {"value": True}),
    ("post", "/user-settings/edit-for-user/{aUser}", {"name": "Plugins.enabled_plugins", "value": ["x"]}),
    ("get", "/user-settings/get-for-user/{aUser}/Plugins.enabled_plugins", None),
]


def fill(value, world):
    if isinstance(value, str):
        return value.format(**ids(world))
    if isinstance(value, dict):
        filled = {k: fill(v, world) for k, v in value.items()}
        return {k: int(v) if k == "id" and isinstance(v, str) and v.isdigit() else v for k, v in filled.items()}
    return value


@pytest.mark.parametrize("method,url,body", ADMIN_ONLY)
def test_regular_users_cannot_use_admin_routes(world, call, method, url, body):
    response = call(world["bob"]["user"], method, fill(url, world), fill(body, world))
    assert response.status_code == 403, response.data


def test_admin_routes_work_for_admins(world, call):
    root = world["root"]
    assert call(root, "get", "/users/index").status_code == 200
    assert call(root, "get", fill("/users/view/{aUser}", world)).status_code == 200
    assert call(root, "post", "/instance/settings/edit/fleet_watching_enabled", {"value": False}).status_code == 200


@pytest.mark.parametrize("method,url,body", [
    ("get", "/servers/get/{aServer}", None),
    ("get", "/fleets/get/{aFleet}", None),
    ("get", "/servers/index/{aFleet}", None),
    ("get", "/user-settings/view/{aSetting}", None),
    ("post", "/user-settings/edit", {"id": "{aSetting}", "value": ["x"]}),
    ("post", "/user-settings/delete/{aSetting}", None),
    ("post", "/pinlists/delete/{aPin}", None),
])
def test_cannot_reach_resources_of_another_user(world, call, method, url, body):
    response = call(world["bob"]["user"], method, fill(url, world), fill(body, world))
    payload = response.get_json(silent=True)
    assert response.status_code == 404 or payload in ({}, [], None), (response.status_code, payload)


def test_cannot_add_servers_to_the_fleet_of_another_user(world, call, db):
    from application.DBModels import Server
    response = call(world["bob"]["user"], "post", fill("/servers/add/{aFleet}", world),
                    {"name": "intruder", "url": "https://x.test", "authkey": "K" * 40})
    assert response.status_code == 404
    assert Server.query.filter_by(name="intruder").first() is None


def test_pinlist_actions_only_target_own_servers(world, call, monkeypatch):
    import application.models.pinlists as pinlistsModel
    requests = []
    monkeypatch.setattr(pinlistsModel, "mispPostRequest", lambda server, *a, **k: requests.append(server.id) or {})
    monkeypatch.setattr(pinlistsModel, "mispGetRequest", lambda server, *a, **k: requests.append(server.id) or {})
    monkeypatch.setattr(pinlistsModel, "batchRequest", lambda reqs: [requests.append(r["server"].id) for r in reqs] and [])
    bob = world["bob"]["user"]
    for url in ["/pinlists/publishEventOnServer/{aServer}/{bPin}", "/pinlists/refreshServerEntry/{aServer}/{bPin}",
                "/pinlists/deleteFromServer/{aServer}/{bPin}", "/pinlists/deleteFromServers/{aFleet}/{bPin}",
                "/pinlists/refreshAllServers/{aFleet}/{bPin}"]:
        call(bob, "post", fill(url, world))
    assert world["alice"]["server"].id not in requests


def test_self_service(world, call, db):
    from application.DBModels import User
    bob = world["bob"]["user"]
    me = call(bob, "get", "/users/view/me")
    assert me.status_code == 200 and me.get_json()["email"] == "bob@test.local"

    key = call(bob, "post", "/users/genAPIKey/me").get_json()["token"]
    assert key

    # Editing oneself works, but not granting oneself the admin role
    response = call(bob, "post", "/users/edit", {"id": bob.id, "comment": "x", "is_admin": True})
    assert response.status_code == 200
    db.session.expire_all()
    assert db.session.get(User, bob.id).is_admin is False

    settings = call(bob, "get", "/user-settings/index").get_json()
    assert {s["user"] for s in settings} == {bob.id}


def test_admins_manage_roles_but_not_their_own(world, call, db):
    from application.DBModels import User
    root, alice = world["root"], world["alice"]["user"]
    call(root, "post", "/users/edit", {"id": alice.id, "is_admin": True})
    call(root, "post", "/users/edit", {"id": root.id, "is_admin": False})
    db.session.expire_all()
    assert db.session.get(User, alice.id).is_admin is True
    assert db.session.get(User, root.id).is_admin is True
    assert call(root, "post", f"/users/delete/{root.id}").status_code == 400
    call(root, "post", "/users/edit", {"id": alice.id, "is_admin": False})


def test_user_apikeys_are_never_returned(world, call):
    root = world["root"]
    for url in ["/users/index", "/users/view/me", fill("/users/get/{aUser}", world)]:
        payload = call(root, "get", url).get_json()
        for user in payload if isinstance(payload, list) else [payload]:
            assert "apikey" not in user, url
            assert "has_apikey" in user and "is_admin" in user, url
