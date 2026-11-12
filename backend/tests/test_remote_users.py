"""User administration on a MISP instance: its user list, and the organisations and roles a new user can get"""
import pytest

ORGS = [
    {"Organisation": {"id": "9", "name": "CIRCL", "local": True}},
    {"Organisation": {"id": "1", "name": "ADMIN", "local": True}},
    {"Organisation": {"id": "65", "name": "badorg", "local": True}},
    {"Organisation": {"id": "70", "name": "Remote org", "local": False}},
]
ROLES = [
    {"Role": {"id": "2", "name": "Org Admin", "default_role": False}},
    {"Role": {"id": "3", "name": "User", "default_role": True}},
    {"Role": {"id": "6", "name": "Read Only", "default_role": False}},
]


@pytest.fixture()
def owner(db, make_user):
    from application.DBModels import Fleet, Server
    user = make_user("remote-users@test.local")
    fleet = Fleet(name="remote users fleet", description="", user_id=user.id, timestamp=1)
    db.session.add(fleet)
    db.session.commit()
    server = Server(name="misp-a", url="https://misp-a.test", authkey="K" * 40, fleet_id=fleet.id, user_id=user.id)
    db.session.add(server)
    db.session.commit()
    yield {"user": user, "server": server}
    db.session.delete(server)
    db.session.delete(fleet)
    db.session.commit()


@pytest.fixture()
def misp(monkeypatch):
    """Answers of the MISP instance, by path"""
    import application.models.serverManagement as serverManagementModel
    import application.controllers.servers as serversController
    answers = {}

    def fakeGet(server, url, *args, **kwargs):
        return answers.get(url.lstrip("/"), {"error": "Not found"})
    monkeypatch.setattr(serverManagementModel, "mispGetRequest", fakeGet)
    monkeypatch.setattr(serversController, "mispGetRequest", fakeGet)
    return answers


@pytest.fixture()
def call(client, auth_headers):
    def _call(user, url):
        return client.get(url, headers=auth_headers(user))
    return _call


def test_options_list_local_organisations_and_roles_by_name(owner, misp, call):
    misp["organisations/index/scope:local"] = ORGS
    misp["roles/index"] = ROLES
    response = call(owner["user"], f"/server-management/user/add-options/{owner['server'].id}")
    assert response.status_code == 200
    data = response.get_json()
    assert [org["name"] for org in data["organisations"]] == ["ADMIN", "badorg", "CIRCL"]
    assert data["organisations"][0] == {"id": "1", "name": "ADMIN"}
    assert [role["name"] for role in data["roles"]] == ["Org Admin", "Read Only", "User"]
    assert [role["name"] for role in data["roles"] if role["default"]] == ["User"]


@pytest.mark.parametrize("failing", ["organisations/index/scope:local", "roles/index"])
def test_options_report_what_misp_answered(owner, misp, call, failing):
    misp["organisations/index/scope:local"] = ORGS
    misp["roles/index"] = ROLES
    misp[failing] = {"error": "Server unreachable"}
    response = call(owner["user"], f"/server-management/user/add-options/{owner['server'].id}")
    assert response.status_code == 502
    assert "Server unreachable" in response.get_json()["message"]


def test_options_of_another_users_server_are_not_found(owner, misp, call, make_user):
    misp["organisations/index/scope:local"] = ORGS
    misp["roles/index"] = ROLES
    other = make_user("remote-users-other@test.local")
    assert call(other, f"/server-management/user/add-options/{owner['server'].id}").status_code == 404


def test_user_list(owner, misp, call):
    users = [{"User": {"id": "1", "email": "admin@misp.test"}, "Organisation": {"id": "1", "name": "ADMIN"}}]
    misp["admin/users/index"] = users
    response = call(owner["user"], f"/servers/getUsers/{owner['server'].id}")
    assert response.status_code == 200 and response.get_json() == users


def test_user_list_reports_misp_errors(owner, misp, call):
    misp["admin/users/index"] = {"error": "Server unreachable"}
    response = call(owner["user"], f"/servers/getUsers/{owner['server'].id}")
    assert response.status_code == 502 and "Server unreachable" in response.get_json()["message"]


def test_user_list_of_another_users_server_is_not_found(owner, misp, call, make_user):
    other = make_user("remote-users-other@test.local")
    assert call(other, f"/servers/getUsers/{owner['server'].id}").status_code == 404
