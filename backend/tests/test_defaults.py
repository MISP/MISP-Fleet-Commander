"""Accounts with the documented default password must change it before anything else, and the token signing
secret persists across restarts"""
import sqlite3

import jwt
import pytest


@pytest.fixture()
def flagged(db, make_user):
    user = make_user("default@test.local")
    user.must_change_password = True
    db.session.commit()
    yield user
    user.password = "Password1234"
    user.must_change_password = False
    db.session.commit()


def login(client, email, password):
    return client.post("/login", json={"email": email, "password": password})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_tells_the_ui_a_password_change_is_required(app, client, flagged):
    token = login(client, "default@test.local", "Password1234").get_json()["access_token"]
    payload = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
    assert payload["data"]["user"]["must_change_password"] is True


def test_only_the_password_change_is_available(client, flagged, auth_headers, socket_client):
    headers = auth_headers(flagged)
    for method, url in [("get", "/fleets/index"), ("get", "/users/index"), ("get", "/pinlists/index"),
                        ("post", "/users/genAPIKey/me"), ("post", "/users/edit")]:
        response = getattr(client, method)(url, headers=headers, json={})
        assert response.status_code == 403 and response.get_json()["password_change_required"] is True, url
    assert client.get("/users/view/me", headers=headers).status_code == 200
    assert not socket_client(user=flagged).is_connected()


@pytest.mark.parametrize("current,new,message", [
    ("wrong-password", "A-much-better-password", "current password is incorrect"),
    ("Password1234", "short", "at least 12 characters"),
    ("Password1234", "Password1234", "different from the current one"),
])
def test_password_change_is_validated(client, flagged, auth_headers, current, new, message):
    response = client.post("/users/change-password", headers=auth_headers(flagged),
                           json={"current_password": current, "new_password": new})
    assert response.status_code == 400 and message in response.get_json()["message"]


def test_changing_the_password_unlocks_the_account(app, client, flagged, auth_headers, db, socket_client):
    response = client.post("/users/change-password", headers=auth_headers(flagged),
                           json={"current_password": "Password1234", "new_password": "A-much-better-password"})
    assert response.status_code == 200
    token = response.get_json()["access_token"]
    assert jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["data"]["user"]["must_change_password"] is False
    assert client.get("/fleets/index", headers=bearer(token)).status_code == 200
    assert socket_client(user=flagged).is_connected()
    assert login(client, "default@test.local", "Password1234").status_code == 401
    assert login(client, "default@test.local", "A-much-better-password").status_code == 200


def test_secret_key_file_is_generated_once(tmp_path):
    from application import crypto
    path = tmp_path / "secret_key"
    secret = crypto.readOrCreateSecretKey(path)
    assert len(secret) == 64 and path.stat().st_mode & 0o777 == 0o600
    assert crypto.readOrCreateSecretKey(path) == secret


def test_production_processes_share_the_generated_secret(flask_cli):
    """Without SECRET_KEY, every process used to pick its own random secret: tokens broke on restart"""
    script = "from application import create_app; print(create_app().config['SECRET_KEY'])"
    secretFile = flask_cli.db_path.parent / "secret_key"
    runs = [flask_cli.python(script, FLASK_CONFIG="config.ProductionConfig", SECRET_KEY="",
                             MFC_SECRET_KEY_FILE=str(secretFile)) for _ in range(2)]
    assert all(run.returncode == 0 for run in runs), runs[0].stderr
    secrets = {run.stdout.strip().splitlines()[-1] for run in runs}
    assert secrets == {secretFile.read_text().strip()}


def test_migration_flags_accounts_using_the_default_password(flask_cli):
    import bcrypt
    flask_cli.upgrade("e2a9c4f7b3d1")
    insert = ("INSERT INTO users (email, created, updated, hashed_password, is_admin) "
              "VALUES (?, '2026-01-01', '2026-01-01', ?, 0)")
    with sqlite3.connect(flask_cli.db_path) as connection:
        connection.execute(insert, ("changed@test.local", bcrypt.hashpw(b"Another-password", bcrypt.gensalt(4)).decode()))
        # Accounts created from the application stored their hash as bytes
        connection.execute(insert, ("created@test.local", bcrypt.hashpw(b"Password1234", bcrypt.gensalt(4))))
    flask_cli.upgrade()
    with sqlite3.connect(flask_cli.db_path) as connection:
        flags = dict(connection.execute("SELECT email, must_change_password FROM users").fetchall())
        types = {row[0] for row in connection.execute("SELECT typeof(hashed_password) FROM users")}
    assert flags == {"admin@admin.test": 1, "changed@test.local": 0, "created@test.local": 1}
    assert types == {"text"}


def test_password_hashes_are_stored_as_text(db, make_user):
    from sqlalchemy import text
    user = make_user("hash@test.local")
    stored = db.session.execute(text("SELECT typeof(hashed_password) FROM users WHERE id = :id"), {"id": user.id}).scalar()
    assert stored == "text"
    assert user.verify_password("Password1234")
