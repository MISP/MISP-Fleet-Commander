"""Passwords an administrator sets are long enough and must be changed at the next login; users change their own
password only by proving they know the current one"""
import pytest

LONG_ENOUGH = "Temporary-pass-1"


@pytest.fixture()
def call(client, auth_headers):
    def _call(user, method, url, json=None):
        return getattr(client, method)(url, headers=auth_headers(user), json=json)
    return _call


@pytest.fixture()
def people(db, make_user):
    from application.DBModels import User
    admin, user = make_user("pw-admin@test.local", is_admin=True), make_user("pw-user@test.local")
    yield {"admin": admin, "user": user}
    for email in ("pw-new@test.local",):
        created = User.query.filter_by(email=email).first()
        if created is not None:
            db.session.delete(created)
    for person in (admin, user):
        person.password, person.must_change_password = "Password1234", False
    db.session.commit()


def reload(db, user):
    from application.DBModels import User
    db.session.expire_all()
    return db.session.get(User, user.id)


def login(client, email, password):
    return client.post("/login", json={"email": email, "password": password})


@pytest.mark.parametrize("password", [None, "", "short", "x" * 11])
def test_added_users_need_a_long_enough_password(people, call, password):
    from application.DBModels import User
    payload = {"email": "pw-new@test.local"}
    if password is not None:
        payload["password"] = password
    response = call(people["admin"], "post", "/users/add", payload)
    assert response.status_code == 400 and response.get_json()["field"] == "password"
    assert User.query.filter_by(email="pw-new@test.local").first() is None


def test_added_users_need_an_email(people, call):
    response = call(people["admin"], "post", "/users/add", {"email": " ", "password": LONG_ENOUGH})
    assert response.status_code == 400 and response.get_json()["field"] == "email"


def test_added_users_must_change_their_password(people, call, client):
    response = call(people["admin"], "post", "/users/add", {"email": "pw-new@test.local", "password": LONG_ENOUGH})
    assert response.status_code == 200 and response.get_json()["must_change_password"] is True
    token = login(client, "pw-new@test.local", LONG_ENOUGH).get_json()["access_token"]
    blocked = client.get("/fleets/index", headers={"Authorization": f"Bearer {token}"})
    assert blocked.status_code == 403 and blocked.get_json()["password_change_required"] is True


def test_password_set_by_an_admin_must_be_changed(people, call, db):
    admin, user = people["admin"], people["user"]
    tooShort = call(admin, "post", "/users/edit", {"id": user.id, "password": "short"})
    assert tooShort.status_code == 400 and tooShort.get_json()["field"] == "password"
    assert reload(db, user).verify_password("Password1234")

    assert call(admin, "post", "/users/edit", {"id": user.id, "password": LONG_ENOUGH}).status_code == 200
    user = reload(db, user)
    assert user.verify_password(LONG_ENOUGH) and user.must_change_password is True


def test_empty_password_leaves_it_unchanged(people, call, db):
    admin, user = people["admin"], people["user"]
    response = call(admin, "post", "/users/edit", {"id": user.id, "password": "", "email": "pw-user@test.local"})
    assert response.status_code == 200
    user = reload(db, user)
    assert user.verify_password("Password1234") and user.must_change_password is False


@pytest.mark.parametrize("who", ["admin", "user"])
def test_own_password_is_not_changed_through_edit(people, call, db, who):
    person = people[who]
    for target in (person.id, "me"):
        response = call(person, "post", "/users/edit", {"id": target, "password": LONG_ENOUGH})
        assert response.status_code == 400 and response.get_json()["field"] == "password"
    person = reload(db, person)
    assert person.verify_password("Password1234") and person.must_change_password is False


def test_must_change_password_cannot_be_cleared_through_edit(people, call, db):
    admin, user = people["admin"], people["user"]
    call(admin, "post", "/users/edit", {"id": user.id, "password": LONG_ENOUGH})
    # Blocked anyway until the password is changed, and the flag is not an editable field
    call(user, "post", "/users/edit", {"id": user.id, "must_change_password": False})
    call(admin, "post", "/users/edit", {"id": user.id, "must_change_password": False})
    assert reload(db, user).must_change_password is True


def test_forced_change_then_normal_use(people, call, client, db):
    admin, user = people["admin"], people["user"]
    call(admin, "post", "/users/edit", {"id": user.id, "password": LONG_ENOUGH})
    token = login(client, "pw-user@test.local", LONG_ENOUGH).get_json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    changed = client.post("/users/change-password", headers=headers,
                          json={"current_password": LONG_ENOUGH, "new_password": "My-own-password-1"})
    assert changed.status_code == 200
    fresh = {"Authorization": f"Bearer {changed.get_json()['access_token']}"}
    assert client.get("/fleets/index", headers=fresh).status_code == 200
    assert reload(db, user).must_change_password is False
