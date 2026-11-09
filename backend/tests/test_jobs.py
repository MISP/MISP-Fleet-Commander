"""Jobs and their per-server results: what is stored (redacted, bounded), counters and final status, what happens
when the user, fleet or servers they mention are deleted, retention and the migration"""
import json
import time
import uuid

import pytest

DAY = 86400


@pytest.fixture(autouse=True)
def _app(app):
    """The models must be imported after the app is built, even by tests that only use pure functions"""
    return app


@pytest.fixture()
def fleetWithServers(db, make_user):
    from application.DBModels import Fleet, Server
    user = make_user(f"jobs-{uuid.uuid4().hex[:8]}@test.test")
    fleet = Fleet(name="Jobs fleet", description="", user_id=user.id, timestamp=1)
    db.session.add(fleet)
    db.session.commit()
    servers = []
    for i in range(3):
        server = Server(name=f"misp-{i}", url=f"https://misp-{i}.test", user_id=user.id, fleet_id=fleet.id)
        db.session.add(server)
        servers.append(server)
    db.session.commit()
    return user, fleet, servers


# Redaction

@pytest.mark.parametrize("key", ["password", "Password", "authkey", "auth_key", "Auth-Key", "apikey", "api_key",
                                 "APIKey", "token", "access_token", "csrf_token", "secret", "client_secret",
                                 "salt", "encryption_key", "private_key", "new_password", "passwd"])
def test_credential_keys_are_redacted(key):
    from application.models.jobs import redact
    assert redact({key: "s3cr3t", "keep": "visible"}) == {key: "***", "keep": "visible"}


def test_redaction_reaches_nested_dicts_and_lists():
    from application.models.jobs import redact
    data = {"users": [{"email": "a@a.test", "authkey": "k1"}, {"email": "b@b.test", "authkey": "k2"}],
            "Server": {"settings": {"redis_password": "p", "port": 6379}}}
    assert redact(data) == {
        "users": [{"email": "a@a.test", "authkey": "***"}, {"email": "b@b.test", "authkey": "***"}],
        "Server": {"settings": {"redis_password": "***", "port": 6379}},
    }


def test_records_under_a_credential_like_model_name_are_redacted_inside():
    from application.models.jobs import redact
    data = {"AuthKey": {"id": 9, "user_id": 3, "authkey": "k" * 40, "authkey_start": "kkkk"},
            "Tokens": [{"token": "t", "comment": "ci"}]}
    assert redact(data) == {"AuthKey": {"id": 9, "user_id": 3, "authkey": "***", "authkey_start": "***"},
                            "Tokens": [{"token": "***", "comment": "ci"}]}


def test_redaction_does_not_modify_its_input():
    from application.models.jobs import redact
    data = {"authkey": "k", "nested": {"token": "t"}}
    redact(data)
    assert data == {"authkey": "k", "nested": {"token": "t"}}


def test_empty_credentials_stay_empty_so_the_log_tells_they_were_cleared():
    from application.models.jobs import redact
    assert redact({"password": "", "authkey": None}) == {"password": "", "authkey": None}


@pytest.mark.parametrize("naming_key", ["setting", "setting_name", "name", "key"])
def test_the_value_of_a_named_secret_setting_is_redacted(naming_key):
    from application.models.jobs import redact
    assert redact({naming_key: "Plugin.ZeroMQ_redis_password", "value": "p"}) == \
        {naming_key: "Plugin.ZeroMQ_redis_password", "value": "***"}
    assert redact({naming_key: "MISP.live", "value": True}) == {naming_key: "MISP.live", "value": True}


@pytest.mark.parametrize("setting, sensitive", [
    ("MISP.redis_password", True),
    ("Plugin.ZeroMQ_redis_password", True),
    ("Security.salt", True),
    ("Security.encryption_key", True),
    ("Plugin.S3_aws_secret_key", True),
    ("GnuPG.password", True),
    ("Security.password_policy_length", False),   # Settings about credentials, not credentials
    ("Security.password_policy_complexity", False),
    ("Security.advanced_authkeys", False),
    ("MISP.authkey_keep_session", False),
    ("MISP.live", False),
])
def test_setting_names_are_judged_by_their_last_word(setting, sensitive):
    from application.models.jobs import redact
    stored = redact({"setting": setting, "value": "v"})["value"]
    assert stored == ("***" if sensitive else "v")


def test_non_credential_keys_are_kept():
    from application.models.jobs import redact
    data = {"setting": "MISP.live", "value": True, "server_ids": [1, 2], "keyword": "x", "monkey": 1}
    assert redact(data) == data


def test_redact_value_uses_the_name():
    from application.models.jobs import redactValue
    assert redactValue("Security.salt", "abc") == "***"
    assert redactValue("MISP.redis_password", "") == ""
    assert redactValue("MISP.live", False) is False
    assert redactValue("MISP.live", {"token": "t"}) == {"token": "***"}


# Response size

def test_small_responses_are_stored_as_json():
    from application.models.jobs import boundedResponse
    assert boundedResponse({"saved": True, "authkey": "k"}) == ({"saved": True, "authkey": "***"}, False)
    assert boundedResponse(None) == (None, False)


def test_large_responses_are_cut_to_a_preview():
    from application.models.jobs import RESPONSE_MAX_BYTES, boundedResponse
    response = {"rows": ["é" * 100] * 2000}
    stored, truncated = boundedResponse(response)
    assert truncated is True
    assert isinstance(stored, str)
    assert len(stored.encode("utf-8")) <= RESPONSE_MAX_BYTES
    assert stored.startswith('{"rows": [')


def test_responses_json_cannot_represent_are_stored_as_text():
    from application.models.jobs import boundedResponse
    stored, truncated = boundedResponse({"when": time, "raw": b"x"})
    assert truncated is False
    json.dumps(stored)


# Status

@pytest.mark.parametrize("succeeded, failed, cancelled, expected", [
    (3, 0, False, "done"),
    (0, 0, False, "done"),     # Every unit skipped
    (2, 1, False, "partial"),
    (0, 3, False, "failed"),
    (2, 0, True, "cancelled"),
])
def test_final_status(succeeded, failed, cancelled, expected):
    from application.models.jobs import finalStatus
    assert finalStatus(succeeded, failed, cancelled) == expected


# Recording

def test_a_job_records_its_results_and_counters(db, fleetWithServers):
    import application.models.jobs as jobModel
    from application.DBModels import Job
    user, fleet, servers = fleetWithServers
    job = jobModel.create(user, "plugin_action", servers, params={"plugin": "LiveMode", "authkey": "k"},
                          title="Enable live mode", fleet=fleet)
    assert job.status == "queued" and job.total == 3 and len(job.id) == 36
    assert job.params == {"plugin": "LiveMode", "authkey": "***"}
    assert (job.user_email, job.fleet_name) == (user.email, "Jobs fleet")

    jobModel.start(job)
    assert job.status == "running" and job.started is not None
    jobModel.recordResult(job.results[0], "ok", http_status=200, summary="Saved", response={"saved": True},
                       before={"value": False}, started=time.time())
    jobModel.recordResult(job.results[1], "error", http_status=500, summary="x" * 5000)
    jobModel.recordResult(job.results[2], "skipped", summary="Already enabled")
    jobModel.finish(job)

    stored = db.session.get(Job, job.id)
    assert (stored.status, stored.succeeded, stored.failed) == ("partial", 1, 1)
    assert stored.finished >= stored.started >= stored.created
    assert [r.status for r in stored.results] == ["ok", "error", "skipped"]
    first = stored.results[0]
    assert (first.server_id, first.server_name, first.server_url) == (servers[0].id, "misp-0", "https://misp-0.test")
    assert first.response == {"saved": True} and first.response_truncated is False
    assert first.before == {"value": False}
    assert len(stored.results[1].summary) == 1024


def test_unknown_kinds_and_statuses_are_refused(db, fleetWithServers):
    import application.models.jobs as jobModel
    user, fleet, servers = fleetWithServers
    with pytest.raises(ValueError):
        jobModel.create(user, "format_disk", servers)
    job = jobModel.create(user, "rest_query", servers)
    with pytest.raises(ValueError):
        jobModel.recordResult(job.results[0], "maybe")


def test_a_cancelled_job_is_cancelled_whatever_its_counters(db, fleetWithServers):
    import application.models.jobs as jobModel
    user, fleet, servers = fleetWithServers
    job = jobModel.create(user, "rest_query", servers)
    jobModel.recordResult(job.results[0], "ok")
    jobModel.recordResult(job.results[1], "cancelled")
    jobModel.recordResult(job.results[2], "cancelled")
    jobModel.finish(job, cancelled=True)
    assert (job.status, job.succeeded, job.failed) == ("cancelled", 1, 0)


# Deletions: the history stays, without pointing at whatever reuses the deleted IDs

def test_deleting_a_server_keeps_its_results_detached(db, fleetWithServers):
    import application.models.jobs as jobModel
    from application.DBModels import JobResult
    user, fleet, servers = fleetWithServers
    job = jobModel.create(user, "plugin_action", servers, fleet=fleet)
    result = jobModel.recordResult(job.results[0], "ok")
    resultId, serverId = result.id, servers[0].id
    db.session.delete(servers[0])
    db.session.commit()
    db.session.expire_all()
    stored = db.session.get(JobResult, resultId)
    assert stored.server_id is None
    assert stored.server_name == "misp-0"
    assert JobResult.query.filter_by(server_id=serverId).count() == 0


def test_deleting_a_fleet_keeps_its_jobs_detached(db, fleetWithServers):
    import application.models.jobs as jobModel
    from application.DBModels import Job
    user, fleet, servers = fleetWithServers
    job = jobModel.create(user, "plugin_action", servers, fleet=fleet)
    jobModel.recordResult(job.results[0], "ok")
    jobId = job.id
    db.session.delete(fleet)  # Deletes its servers too
    db.session.commit()
    db.session.expire_all()
    stored = db.session.get(Job, jobId)
    assert stored.fleet_id is None and stored.fleet_name == "Jobs fleet"
    assert [r.server_id for r in stored.results] == [None, None, None]


def test_deleting_a_user_keeps_their_jobs_detached(db, make_user):
    import application.models.jobs as jobModel
    from application.DBModels import Job
    user = make_user(f"leaving-{uuid.uuid4().hex[:8]}@test.test")
    email = user.email
    job = jobModel.create(user, "server_management", [])
    jobId = job.id
    db.session.delete(user)
    db.session.commit()
    db.session.expire_all()
    stored = db.session.get(Job, jobId)
    assert stored.user_id is None and stored.user_email == email


# Retention

def test_purge_deletes_jobs_older_than_the_retention_with_their_results(db, fleetWithServers):
    import application.models.jobs as jobModel
    from application.DBModels import Job, JobResult
    user, fleet, servers = fleetWithServers
    now = time.time()
    old = jobModel.create(user, "rest_query", servers)
    jobModel.recordResult(old.results[0], "ok")
    old.created = now - 91 * DAY
    recent = jobModel.create(user, "rest_query", servers)
    jobModel.recordResult(recent.results[0], "ok")
    recent.created = now - 89 * DAY
    db.session.commit()
    oldId, recentId = old.id, recent.id

    assert jobModel.purge(90, now=now) >= 1
    db.session.expire_all()
    assert db.session.get(Job, oldId) is None
    assert JobResult.query.filter_by(job_id=oldId).count() == 0
    assert db.session.get(Job, recentId) is not None
    assert JobResult.query.filter_by(job_id=recentId).count() == 3


def test_the_purge_task_reads_the_retention_setting(db, fleetWithServers, monkeypatch):
    import application.models.jobs as jobModel
    import application.models.setting as settingModel
    from application.DBModels import Job
    from application.workers import tasks
    user, fleet, servers = fleetWithServers
    job = jobModel.create(user, "rest_query", servers)
    job.created = time.time() - 8 * DAY
    db.session.commit()
    jobId = job.id
    monkeypatch.setattr(settingModel, "getRefreshValue",
                        lambda name: 7 if name == "job_retention_days" else settingModel.getValue(name))
    tasks.purgeOldJobs.call_local()
    db.session.expire_all()
    assert db.session.get(Job, jobId) is None


def test_retention_setting_is_validated():
    import application.models.setting as settingModel
    assert settingModel.getValue("job_retention_days") == 90
    assert settingModel.validate("job_retention_days", 30) == 30
    for bad in (0, 3651, 1.5, "abc"):
        with pytest.raises(settingModel.SettingError):
            settingModel.validate("job_retention_days", bad)


# Migration

def test_migration_creates_and_drops_the_job_tables(flask_cli):
    listTables = ("import sqlite3, os; c = sqlite3.connect(os.environ['SQLALCHEMY_DATABASE_URI']);"
                  "print([r[0] for r in c.execute(\"select name from sqlite_master where type='table'\")])")
    flask_cli.upgrade()
    tables = flask_cli.python(listTables).stdout
    assert "'jobs'" in tables and "'job_results'" in tables
    downgraded = flask_cli.run("db", "downgrade", "b3f6a9d2c7e4")
    assert downgraded.returncode == 0, downgraded.stderr
    tables = flask_cli.python(listTables).stdout
    assert "'jobs'" not in tables and "'job_results'" not in tables
