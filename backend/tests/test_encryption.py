"""MISP authkeys are encrypted at rest, and a missing or wrong key is reported at startup"""
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet, MultiFernet
from sqlalchemy import text

from application import crypto

AUTHKEY = "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789wxyz"
BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture()
def keep_cipher():
    """Tests below swap the module's cipher: put the session's one back afterwards"""
    saved = crypto._cipher
    yield
    crypto._cipher = saved


@pytest.fixture()
def server(db, make_user):
    from application.DBModels import Fleet, Server
    user = make_user("crypto@test.local")
    fleet = Fleet(name="crypto fleet", description="", user_id=user.id, timestamp=1)
    db.session.add(fleet)
    db.session.commit()
    server = Server(name="crypto-misp", url="https://crypto.test", authkey=AUTHKEY, fleet_id=fleet.id, user_id=user.id)
    db.session.add(server)
    db.session.commit()
    yield server
    db.session.delete(server)
    db.session.delete(fleet)
    db.session.commit()


def storedValue(db, server):
    return db.session.execute(text("SELECT authkey_enc FROM servers WHERE id = :id"), {"id": server.id}).scalar()


def fakeApp(tmp_path, key=None):
    return SimpleNamespace(config={"ENCRYPTION_KEY": key, "ENCRYPTION_KEY_FILE": str(tmp_path / "encryption_key")},
                           logger=SimpleNamespace(warning=lambda message: None))


def test_authkeys_are_stored_encrypted(db, server):
    stored = storedValue(db, server)
    assert stored and AUTHKEY not in stored
    db.session.expire_all()
    assert server.authkey == AUTHKEY


def test_clearing_the_authkey_stores_nothing(db, server):
    server.authkey = ""
    db.session.commit()
    assert storedValue(db, server) is None and server.authkey is None


def test_ciphertext_is_not_sent_to_clients(server, client, auth_headers):
    payload = client.get(f"/servers/get/{server.id}", headers=auth_headers(server.user)).get_json()
    assert "authkey_enc" not in payload and "authkey" not in payload
    assert payload["has_authkey"] is True


def test_new_installs_get_a_private_key_file(tmp_path, keep_cipher):
    crypto.init(fakeApp(tmp_path), lambda: None)
    keyFile = tmp_path / "encryption_key"
    assert len(crypto.readKeyFile(keyFile)) == 1
    assert keyFile.stat().st_mode & 0o777 == 0o600
    assert crypto.decrypt(crypto.encrypt("x")) == "x"
    # The next start reuses it
    key = keyFile.read_text()
    crypto.init(fakeApp(tmp_path), lambda: None)
    assert keyFile.read_text() == key


def test_missing_key_with_encrypted_data_fails(tmp_path, keep_cipher):
    token = Fernet(Fernet.generate_key()).encrypt(b"x").decode()
    with pytest.raises(crypto.EncryptionKeyError, match="no encryption key is configured"):
        crypto.init(fakeApp(tmp_path), lambda: token)
    assert not (tmp_path / "encryption_key").exists()


def test_wrong_key_fails(tmp_path, keep_cipher):
    token = Fernet(Fernet.generate_key()).encrypt(b"x").decode()
    with pytest.raises(crypto.EncryptionKeyError, match="does not decrypt"):
        crypto.init(fakeApp(tmp_path, Fernet.generate_key().decode()), lambda: token)


def test_malformed_key_fails(tmp_path, keep_cipher):
    with pytest.raises(crypto.EncryptionKeyError, match="malformed"):
        crypto.init(fakeApp(tmp_path, "not-a-key"), lambda: None)


def test_rotate_key(app, db, server, keep_cipher):
    oldKey, newKey = os.environ["MFC_ENCRYPTION_KEY"], Fernet.generate_key().decode()
    crypto._cipher = crypto.buildCipher(crypto.parseKeys(f"{newKey},\n{oldKey}"))
    result = app.test_cli_runner().invoke(args=["security", "rotate-key"])
    assert result.exit_code == 0, result.output
    stored = storedValue(db, server)
    assert Fernet(newKey).decrypt(stored.encode()).decode() == AUTHKEY
    # Put the session key back on the row for the other tests
    crypto._cipher = MultiFernet([Fernet(oldKey)])
    server.authkey = AUTHKEY
    db.session.commit()


def flask(args, env):
    return subprocess.run([sys.executable, "-m", "flask", *args], cwd=BACKEND_DIR, env=env,
                          capture_output=True, text=True, timeout=120)


def test_migration_encrypts_existing_authkeys(tmp_path):
    dbPath = tmp_path / "upgrade.db"
    env = dict(os.environ, FLASK_APP="wsgi.py", FLASK_CONFIG="config.DevelopmentConfig",
               SQLALCHEMY_DATABASE_URI=str(dbPath), SOCKETIO_MESSAGE_QUEUE="", MFC_ENCRYPTION_KEY="", MFC_ENCRYPTION_KEY_FILE=str(tmp_path / "key"))
    before = flask(["db", "upgrade", "c4e1a7d2b9f0"], env)
    assert before.returncode == 0, before.stderr
    with sqlite3.connect(dbPath) as connection:
        connection.execute("INSERT OR IGNORE INTO users (id, email, created, updated, hashed_password, is_admin) "
                           "VALUES (1, 'a@test.local', '2026-01-01', '2026-01-01', 'x', 1)")
        connection.execute("INSERT INTO fleets (id, name, description, user_id, timestamp) VALUES (1, 'f', '', 1, 1)")
        # Enough rows for the table to span several pages, which the migration frees
        connection.executemany("INSERT INTO servers (id, name, uuid, comment, url, skip_ssl, authkey, user_id, fleet_id) "
                               "VALUES (?, 's', ?, '', 'https://s.test', 0, ?, 1, 1)",
                               [(i, f"uuid-{i}", AUTHKEY[:-4] + f"{i:04d}") for i in range(1, 301)])

    after = flask(["db", "upgrade"], env)
    assert after.returncode == 0, after.stderr
    key = (tmp_path / "key").read_text().strip()
    with sqlite3.connect(dbPath) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(servers)")}
        stored = connection.execute("SELECT authkey_enc FROM servers WHERE id = 1").fetchone()[0]
    assert "authkey" not in columns
    assert Fernet(key).decrypt(stored.encode()).decode() == AUTHKEY[:-4] + "0001"
    assert AUTHKEY[:-4].encode() not in dbPath.read_bytes()

    # The app now refuses to start with another key
    wrongKey = flask(["security", "--help"], dict(env, MFC_ENCRYPTION_KEY=Fernet.generate_key().decode()))
    assert wrongKey.returncode != 0 and "does not decrypt" in wrongKey.stderr

    downgraded = flask(["db", "downgrade", "c4e1a7d2b9f0"], env)
    assert downgraded.returncode == 0, downgraded.stderr
    with sqlite3.connect(dbPath) as connection:
        assert connection.execute("SELECT authkey FROM servers WHERE id = 1").fetchone()[0] == AUTHKEY[:-4] + "0001"
