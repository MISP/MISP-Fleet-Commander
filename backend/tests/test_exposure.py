"""Images and configuration need authentication, the login token carries the bare minimum, API keys are stored
hashed, failed logins are throttled and cross-origin access is limited"""
import sqlite3

import jwt
import pytest
from sqlalchemy import text


@pytest.fixture()
def owned(db, make_user):
    """alice owns a fleet, a server and a pinned entry; bob owns nothing"""
    from application.DBModels import Fleet, Server, PinList
    alice, bob = make_user("alice@test.local"), make_user("bob@test.local")
    fleet = Fleet(name="exposure fleet", description="", user_id=alice.id, timestamp=1)
    db.session.add(fleet)
    db.session.commit()
    server = Server(name="exposure-misp", url="https://exposure.test", authkey="K" * 40, fleet_id=fleet.id, user_id=alice.id)
    pin = PinList(model="Event", uuid="00000000-0000-0000-0000-0000000000aa", user_id=alice.id)
    db.session.add_all([server, pin])
    db.session.commit()
    yield {"alice": alice, "bob": bob, "server": server, "pin": pin}
    db.session.delete(pin)
    db.session.delete(server)
    db.session.delete(fleet)
    db.session.commit()


@pytest.fixture()
def png(tmp_path):
    path = tmp_path / "image.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    return path


@pytest.fixture()
def stub_images(monkeypatch, png):
    import application.controllers.pinLists as pinListsController
    monkeypatch.setattr(pinListsController.AvatarGenerator, "getPath", lambda self: str(png))


def test_images_need_authentication(owned, client, stub_images):
    assert client.get(f"/pinlists/getAvatar/{owned['pin'].id}.png").status_code == 401


def test_images_are_only_served_to_their_owner(owned, client, auth_headers, stub_images):
    avatarUrl = f"/pinlists/getAvatar/{owned['pin'].id}.png"
    alice, bob = auth_headers(owned["alice"]), auth_headers(owned["bob"])
    assert client.get(avatarUrl, headers=alice).status_code == 200
    assert client.get(avatarUrl, headers=bob).status_code == 404


def test_login_token_only_identifies_the_user(app, client, make_user):
    user = make_user("token@test.local")
    token = client.post("/login", json={"email": "token@test.local", "password": "Password1234"}).get_json()["access_token"]
    payload = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
    assert payload["data"] == {"user": {"id": user.id, "email": "token@test.local", "is_admin": False,
                                        "must_change_password": False}}


def test_api_keys_are_stored_hashed(owned, client, auth_headers, db):
    alice = owned["alice"]
    key = client.post("/users/genAPIKey/me", headers=auth_headers(alice)).get_json()["token"]
    stored = db.session.execute(text("SELECT apikey_hash FROM users WHERE id = :id"), {"id": alice.id}).scalar()
    assert stored and key not in stored
    assert client.get("/users/view/me", headers={"Authorization": f"Apikey {key}"}).get_json()["email"] == alice.email

    newKey = client.post("/users/genAPIKey/me", headers=auth_headers(alice)).get_json()["token"]
    assert client.get("/users/view/me", headers={"Authorization": f"Apikey {key}"}).status_code == 401
    assert client.get("/users/view/me", headers={"Authorization": f"Apikey {newKey}"}).status_code == 200


def test_new_users_have_no_api_key(make_user):
    assert make_user("nokey@test.local").has_apikey is False


def login(client, email, password):
    return client.post("/login", json={"email": email, "password": password})


def test_failed_logins_are_throttled(client, make_user):
    make_user("throttled@test.local")
    for _ in range(5):
        assert login(client, "throttled@test.local", "wrong").status_code == 401
    locked = login(client, "throttled@test.local", "Password1234")
    assert locked.status_code == 429 and "Try again in 15 minutes" in locked.get_json()["message"]
    # Other accounts are not affected
    make_user("other@test.local")
    assert login(client, "other@test.local", "Password1234").status_code == 200


def test_successful_login_resets_the_failure_count(client, make_user):
    make_user("forgetful@test.local")
    for _ in range(4):
        assert login(client, "forgetful@test.local", "wrong").status_code == 401
    assert login(client, "forgetful@test.local", "Password1234").status_code == 200
    for _ in range(4):
        assert login(client, "forgetful@test.local", "wrong").status_code == 401
    assert login(client, "forgetful@test.local", "Password1234").status_code == 200


def test_email_variants_share_the_failure_count(client, make_user):
    make_user("variant@test.local")
    for email in ["variant@test.local", "VARIANT@test.local", " variant@test.local", "Variant@Test.local", "variant@test.local "]:
        login(client, email, "wrong")
    assert login(client, "variant@test.local", "Password1234").status_code == 429


def allowedOrigin(response):
    return response.headers.get("Access-Control-Allow-Origin")


def test_cross_origin_access(owned, client, auth_headers):
    headers = dict(auth_headers(owned["alice"]), Origin="https://evil.test")
    assert allowedOrigin(client.get(f"/servers/index/{owned['server'].fleet_id}", headers=headers)) is None
    assert allowedOrigin(client.get("/users/view/1", headers=headers)) is None
    # Configured origins are allowed
    headers["Origin"] = "https://extension.test"
    assert allowedOrigin(client.get(f"/servers/index/{owned['server'].fleet_id}", headers=headers)) == "https://extension.test"
    # The enrollment routes of the browser extension work from any page
    headers["Origin"] = "https://misp.example"
    assert allowedOrigin(client.get("/fleets/index", headers=headers)) == "https://misp.example"
    assert allowedOrigin(client.get("/users/view/me", headers=headers)) == "https://misp.example"
    preflight = client.options(f"/servers/add/{owned['server'].fleet_id}", headers={
        "Origin": "https://misp.example", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type"})
    assert allowedOrigin(preflight) == "https://misp.example"


def test_socket_origins():
    from application import socketOriginChecker
    isAllowed = socketOriginChecker(["https://extension.test"])
    environ = {"HTTP_HOST": "mfc.example:5001"}
    assert isAllowed("http://mfc.example:5001", environ)
    assert isAllowed("https://mfc.example:5001", environ)  # TLS terminated by a proxy
    assert isAllowed("https://extension.test", environ)
    assert not isAllowed("https://evil.test", environ)
    assert not isAllowed("https://mfc.example.evil.test", environ)
    assert isAllowed("https://mfc.example", {"HTTP_HOST": "backend:5001", "HTTP_X_FORWARDED_HOST": "mfc.example"})


def test_migration_hashes_existing_api_keys(flask_cli):
    from application.models.auth import hash_API_key
    flask_cli.upgrade("d7f3b2a8c1e5")
    key = "k" * 54
    with sqlite3.connect(flask_cli.db_path) as connection:
        connection.execute("UPDATE users SET apikey = ?", (key,))
    flask_cli.upgrade()
    with sqlite3.connect(flask_cli.db_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
        stored = {row[0] for row in connection.execute("SELECT apikey_hash FROM users")}
    assert "apikey" not in columns
    assert stored == {hash_API_key(key)}
    assert key.encode() not in flask_cli.db_path.read_bytes()
