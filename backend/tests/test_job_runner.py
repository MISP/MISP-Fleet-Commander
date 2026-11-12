"""Running jobs: the runner (results, counters, events, concurrency, cancel), what each kind does on a server, the
single-server writes recorded as jobs, the encrypted parameters, and the default timeout of MISP requests"""
import threading
import time
import uuid

import pytest
import requests


@pytest.fixture(autouse=True)
def _app(app):
    return app


@pytest.fixture()
def fleet(db, make_user):
    from application.DBModels import Fleet, Server
    user = make_user(f"runner-{uuid.uuid4().hex[:8]}@test.test")
    fleet = Fleet(name="Runner fleet", description="", user_id=user.id, timestamp=1)
    db.session.add(fleet)
    db.session.commit()
    servers = []
    for i in range(5):
        server = Server(name=f"misp-{i}", url=f"https://misp-{i}.test", user_id=user.id, fleet_id=fleet.id)
        server.authkey = f"key-{i}"
        db.session.add(server)
        servers.append(server)
    db.session.commit()
    return user, fleet, servers


class Emitter:
    def __init__(self):
        self.progress, self.done = [], []

    def job_progress(self, job, payload):
        self.progress.append(payload)

    def job_done(self, job):
        self.done.append((job.id, job.status))


@pytest.fixture()
def fakeExecute(monkeypatch):
    """Replace what units do: `behaviour[server_name]` → UnitResult, or a callable(server) returning one"""
    import application.models.jobRunner as jobRunner
    from application.models.jobs import UnitResult
    behaviour = {}
    calls = []

    def execute(kind, server, params):
        calls.append((kind, server.name, params))
        outcome = behaviour.get(server.name, UnitResult(True, http_status=200, summary="Done"))
        return outcome(server) if callable(outcome) else outcome
    monkeypatch.setattr(jobRunner, "execute", execute)
    return behaviour, calls


# Creating jobs

def test_a_job_lists_its_servers_as_pending_from_the_start(db, fleet):
    import application.models.jobs as jobModel
    user, theFleet, servers = fleet
    job = jobModel.create(user, "rest_query", servers[:3])
    assert [(r.server_name, r.status) for r in job.results] == [("misp-0", "pending"), ("misp-1", "pending"),
                                                                ("misp-2", "pending")]


def test_parameters_are_stored_redacted_and_encrypted(db, fleet):
    import application.models.jobs as jobModel
    from application.DBModels import Job
    user, theFleet, servers = fleet
    params = {"plugin_id": "mass-user-import", "data": {"users": [{"email": "a@a.test", "password": "Hunter2!x"}]}}
    job = jobModel.create(user, "plugin_action", servers[:1], params=params)
    db.session.expire_all()
    stored = db.session.get(Job, job.id)
    assert stored.params["data"]["users"][0]["password"] == "***"
    assert "Hunter2!x" not in stored.params_enc and "mass-user-import" not in stored.params_enc
    assert stored.secret_params == params
    assert "params_enc" not in jobModel.serializeJob(stored, withResults=True)
    assert "secret_params" not in jobModel.serializeJob(stored)


def test_a_recorded_result_cannot_be_recorded_again(db, fleet):
    import application.models.jobs as jobModel
    user, theFleet, servers = fleet
    job = jobModel.create(user, "rest_query", servers[:1])
    jobModel.recordResult(job.results[0], "ok")
    with pytest.raises(ValueError):
        jobModel.recordResult(job.results[0], "error")
    with pytest.raises(ValueError):
        jobModel.recordResult(job.results[0], "pending")


# The runner

def test_the_runner_records_every_server_and_reports_progress(db, fleet, fakeExecute):
    import application.models.jobRunner as jobRunner
    import application.models.jobs as jobModel
    from application.DBModels import Job
    from application.models.jobs import UnitResult
    behaviour, calls = fakeExecute
    user, theFleet, servers = fleet
    behaviour["misp-1"] = UnitResult(False, http_status=None, summary="Server unreachable")
    behaviour["misp-3"] = UnitResult(False, skipped=True, summary="Already enabled")
    job = jobModel.create(user, "plugin_action", servers, params={"plugin_id": "live-mode", "data": {"x": 1}},
                          fleet=theFleet)
    emitter = Emitter()

    assert jobRunner.run(job.id, emitter, max_concurrency=2) is not None
    db.session.expire_all()
    stored = db.session.get(Job, job.id)
    assert (stored.status, stored.succeeded, stored.failed, stored.total) == ("partial", 3, 1, 5)
    assert {r.server_name: r.status for r in stored.results} == {
        "misp-0": "ok", "misp-1": "error", "misp-2": "ok", "misp-3": "skipped", "misp-4": "ok"}
    assert all(r.finished >= r.started for r in stored.results)
    assert stored.finished >= stored.started
    # The units got the real parameters
    assert {params["data"]["x"] for kind, name, params in calls} == {1}
    # One progress event per server, counting up, then one done event
    assert [p["done"] for p in emitter.progress] == [1, 2, 3, 4, 5]
    assert {p["result"]["server_name"] for p in emitter.progress} == {f"misp-{i}" for i in range(5)}
    assert emitter.progress[-1]["succeeded"] == 3 and emitter.progress[-1]["failed"] == 1
    assert emitter.done == [(job.id, "partial")]


@pytest.mark.parametrize("failures, expected", [(0, "done"), (5, "failed")])
def test_final_status_of_a_run(db, fleet, fakeExecute, failures, expected):
    import application.models.jobRunner as jobRunner
    import application.models.jobs as jobModel
    from application.models.jobs import UnitResult
    behaviour, calls = fakeExecute
    user, theFleet, servers = fleet
    for server in servers[:failures]:
        behaviour[server.name] = UnitResult(False, summary="Nope")
    job = jobModel.create(user, "rest_query", servers)
    assert jobRunner.run(job.id).status == expected


def test_a_job_runs_once(db, fleet, fakeExecute):
    import application.models.jobRunner as jobRunner
    import application.models.jobs as jobModel
    behaviour, calls = fakeExecute
    user, theFleet, servers = fleet
    job = jobModel.create(user, "rest_query", servers[:2])
    jobRunner.run(job.id)
    assert jobRunner.run(job.id) is None
    assert jobRunner.run("no-such-job") is None
    assert len(calls) == 2


def test_concurrency_is_capped(db, fleet, fakeExecute):
    import application.models.jobRunner as jobRunner
    import application.models.jobs as jobModel
    from application.models.jobs import UnitResult
    behaviour, calls = fakeExecute
    user, theFleet, servers = fleet
    lock = threading.Lock()
    state = {"running": 0, "max": 0}

    def slow(server):
        with lock:
            state["running"] += 1
            state["max"] = max(state["max"], state["running"])
        time.sleep(0.05)
        with lock:
            state["running"] -= 1
        return UnitResult(True)
    for server in servers:
        behaviour[server.name] = slow
    job = jobModel.create(user, "rest_query", servers)
    jobRunner.run(job.id, max_concurrency=2)
    assert state["max"] == 2


def test_a_cancel_after_every_server_started_changes_nothing(db, fleet, fakeExecute):
    import application.models.jobRunner as jobRunner
    import application.models.jobs as jobModel
    from application.models.jobs import UnitResult
    behaviour, calls = fakeExecute
    user, theFleet, servers = fleet
    job = jobModel.create(user, "rest_query", servers[:2])

    def cancellingLast(server):
        jobRunner.requestCancel(job.id)
        return UnitResult(False, summary="Server unreachable")
    behaviour["misp-1"] = cancellingLast
    jobRunner.run(job.id, max_concurrency=2)
    assert [r.status for r in job.results] == ["ok", "error"]
    assert job.status == "partial"
    assert not jobRunner.cancelRequested(job.id)


def test_units_not_started_are_cancelled(db, fleet, fakeExecute):
    import application.models.jobRunner as jobRunner
    import application.models.jobs as jobModel
    from application.models.jobs import UnitResult
    behaviour, calls = fakeExecute
    user, theFleet, servers = fleet
    job = jobModel.create(user, "rest_query", servers)

    def cancelling(server):
        jobRunner.requestCancel(job.id)
        return UnitResult(True)
    behaviour["misp-1"] = cancelling
    emitter = Emitter()
    jobRunner.run(job.id, emitter, max_concurrency=1)
    assert [r.status for r in job.results] == ["ok", "ok", "cancelled", "cancelled", "cancelled"]
    assert (job.status, job.succeeded, job.failed) == ("cancelled", 2, 0)
    assert [name for kind, name, params in calls] == ["misp-0", "misp-1"]
    assert len(emitter.progress) == 5 and emitter.done == [(job.id, "cancelled")]
    assert not jobRunner.cancelRequested(job.id)  # The flag goes with the job


def test_a_server_deleted_before_the_run_is_skipped(db, fleet, fakeExecute):
    import application.models.jobRunner as jobRunner
    import application.models.jobs as jobModel
    behaviour, calls = fakeExecute
    user, theFleet, servers = fleet
    job = jobModel.create(user, "rest_query", servers[:2])
    db.session.delete(servers[1])
    db.session.commit()
    db.session.expire_all()
    jobRunner.run(job.id)
    assert [(r.server_name, r.status, r.summary) for r in job.results] == [
        ("misp-0", "ok", "Done"), ("misp-1", "skipped", "The server was deleted")]
    assert job.status == "done"


def test_a_unit_that_cannot_run_is_an_error_not_a_crash(db, fleet, monkeypatch):
    import application.models.jobRunner as jobRunner
    import application.models.jobs as jobModel
    user, theFleet, servers = fleet

    def broken(*args):
        raise RuntimeError("Redis is down")
    monkeypatch.setattr(jobRunner, "runUnit", broken)
    job = jobModel.create(user, "rest_query", servers[:2])
    jobRunner.run(job.id)
    assert [r.status for r in job.results] == ["error", "error"]
    assert job.results[0].summary == "Could not run: Redis is down"
    assert job.status == "failed"


def test_socket_failures_do_not_stop_a_job(db, fleet, fakeExecute):
    import application.models.jobRunner as jobRunner
    import application.models.jobs as jobModel
    user, theFleet, servers = fleet

    class Broken:
        def job_progress(self, *a):
            raise ConnectionError("queue down")

        def job_done(self, *a):
            raise ConnectionError("queue down")
    job = jobModel.create(user, "rest_query", servers[:2])
    assert jobRunner.run(job.id, Broken()).status == "done"


def test_job_events_go_to_the_owner_only(db, fleet, fakeExecute, monkeypatch):
    import application.models.jobRunner as jobRunner
    import application.models.jobs as jobModel
    from application.controllers.websocket import socketEmitter
    user, theFleet, servers = fleet
    events = []
    monkeypatch.setattr(socketEmitter.socketio, "emit", lambda event, data=None, **kw: events.append((event, kw.get("to"))))
    job = jobModel.create(user, "rest_query", servers[:2])
    jobRunner.run(job.id, socketEmitter)
    assert events == [("JOB_STARTED", f"user:{user.id}")] + [("JOB_PROGRESS", f"user:{user.id}")] * 2 + [("JOB_DONE", f"user:{user.id}")]


def test_the_worker_task_reads_the_concurrency_setting(db, fleet, monkeypatch):
    import application.models.jobRunner as jobRunner
    import application.models.jobs as jobModel
    import application.models.setting as settingModel
    from application.workers import tasks
    user, theFleet, servers = fleet
    seen = {}
    monkeypatch.setattr(settingModel, "getRefreshValue",
                        lambda name: 3 if name == "job_max_concurrency" else settingModel.getValue(name))
    monkeypatch.setattr(jobRunner, "run", lambda job_id, emitter, max_concurrency: seen.update(job_id=job_id, n=max_concurrency))
    job = jobModel.create(user, "rest_query", servers[:1])
    tasks.runJob.call_local(job.id)
    assert seen == {"job_id": job.id, "n": 3}


# What each kind does on a server

class FakeResponse:
    def __init__(self, status, body, reason="OK"):
        self.status_code, self._body, self.reason = status, body, reason
        self.headers = {"Content-Type": "application/json"}
        self.url = "https://misp.test/x"
        self.elapsed = 0.1
        self.text = str(body)

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


@pytest.mark.parametrize("url, ok", [
    ("/servers/getVersion", True), ("servers/getVersion", True), ("/a?b=c", True),
    ("https://evil.test/x", False), ("//evil.test/x", False), ("http:/x", False), ("", False), (None, False),
])
def test_rest_queries_only_reach_paths_of_the_server(url, ok):
    from application.models.jobUnits import isRelativePath
    assert isRelativePath(url) is ok


def test_a_rest_query_to_another_host_is_refused_before_sending(db, fleet, monkeypatch):
    import application.models.jobUnits as jobUnits
    user, theFleet, servers = fleet
    sent = []
    monkeypatch.setattr(jobUnits, "mispGetRequest", lambda *a, **k: sent.append(a))
    unit = jobUnits.restQueryUnit(servers[0], {"method": "GET", "url": "https://collector.test/"})
    assert unit.ok is False and "path on the MISP server" in unit.summary and sent == []


@pytest.mark.parametrize("answer, ok, summary", [
    (FakeResponse(200, {"Server": {"id": 1}}), True, "200 OK"),
    (FakeResponse(404, {"message": "Not found"}, "Not Found"), False, "404 Not Found"),
    (FakeResponse(200, {"saved": False, "errors": {"url": ["Invalid"]}}), False, "200 OK: url: Invalid"),
    ({"error": "Server unreachable"}, False, "Server unreachable"),
    ({"error": "Authentication error", "_status_code": 403}, False, "Authentication error"),
])
def test_rest_query_outcomes(db, fleet, monkeypatch, answer, ok, summary):
    import application.models.jobUnits as jobUnits
    user, theFleet, servers = fleet
    monkeypatch.setattr(jobUnits, "mispPostRequest", lambda *a, **k: answer)
    unit = jobUnits.restQueryUnit(servers[0], {"method": "POST", "url": "/servers/edit/1", "data": '{"a": 1}'})
    assert (unit.ok, unit.summary) == (ok, summary)
    assert unit.response is not None


def test_plugin_responses_become_unit_results():
    from application.models.jobUnits import fromPluginResponse
    ok = fromPluginResponse({"status": "success", "data": {"message": "Live mode enabled"},
                             "request_response": {"status_code": 200}})
    assert (ok.ok, ok.http_status, ok.summary) == (True, 200, "Live mode enabled")
    failed = fromPluginResponse({"status": "fail", "data": {}, "error": ["Server unreachable"]})
    assert (failed.ok, failed.http_status, failed.summary) == (False, None, "Server unreachable")
    assert fromPluginResponse({"status": "error", "data": []}).summary == "Failed"


def test_a_partial_plugin_success_is_an_error_unit():
    from application.models.jobUnits import fromPluginResponse
    unit = fromPluginResponse({"status": "success", "error": ["pap - HTTP 403 Forbidden"],
                               "data": {"message": "Successfully disabled 1 taxonomies. 1 taxonomies could not be updated"}})
    assert unit.ok is False
    assert unit.summary == "Successfully disabled 1 taxonomies. 1 taxonomies could not be updated (pap - HTTP 403 Forbidden)"


def test_a_plugin_unit_runs_the_plugin_action(db, fleet, monkeypatch):
    import application
    import application.models.jobUnits as jobUnits
    from application.models.plugins import SuccessPluginResponse
    user, theFleet, servers = fleet
    seen = []

    class Plugin:
        def action(self, server, data):
            seen.append((server.name, data))
            return SuccessPluginResponse({"message": "Done it"})
    plugin = {"id": "fake", "name": "Fake", "features": {"action": True, "quickAction": False}, "instance": Plugin()}
    monkeypatch.setattr(application, "loadedPlugins", [plugin])
    unit = jobUnits.pluginActionUnit(servers[0], {"plugin_id": "fake", "data": {"state": "1"}})
    assert (unit.ok, unit.summary, seen) == (True, "Done it", [("misp-0", {"state": "1"})])
    assert jobUnits.pluginQuickActionUnit(servers[0], {"plugin_id": "fake"}).summary == \
        "Plugin `fake` has no quick action"
    assert jobUnits.pluginActionUnit(servers[0], {"plugin_id": "nope"}).summary == "Unknown plugin `nope`"


def test_a_plugin_that_raises_is_a_failed_unit(db, fleet, monkeypatch):
    import application
    import application.models.jobUnits as jobUnits
    user, theFleet, servers = fleet

    class Plugin:
        def action(self, server, data):
            raise KeyError("state")
    monkeypatch.setattr(application, "loadedPlugins",
                        [{"id": "boom", "name": "Boom", "features": {"action": True}, "instance": Plugin()}])
    unit = jobUnits.execute("plugin_action", servers[0], {"plugin_id": "boom"})
    assert unit.ok is False and "state" in unit.summary


def test_server_management_outcomes(db, fleet, monkeypatch):
    import application.models.jobUnits as jobUnits
    from application.models import serverManagement
    user, theFleet, servers = fleet
    monkeypatch.setattr(serverManagement, "mispPostRequest", lambda *a, **k: FakeResponse(
        403, {"name": "Could not edit", "message": "Could not edit the user.",
              "errors": {"password": ["Too short", "Needs a digit"]}}, "Forbidden"))
    unit = jobUnits.serverManagementUnit(servers[0], {"operation": "set_password", "user_id": 3,
                                                      "payload": {"password": "x", "confirm_password": "x"}})
    assert unit.ok is False and unit.http_status == 403
    assert unit.summary == "Could not edit the user. - password: Too short; Needs a digit"

    monkeypatch.setattr(serverManagement, "mispPostRequest", lambda *a, **k: {"error": "Request timed out"})
    unit = jobUnits.serverManagementUnit(servers[0], {"operation": "set_password", "user_id": 3, "payload": {}})
    assert (unit.ok, unit.summary) == (False, "Request timed out")

    monkeypatch.setattr(serverManagement, "mispPostRequest",
                        lambda *a, **k: {"User": {"id": 3, "disabled": True}, "_status_code": 200})
    unit = jobUnits.serverManagementUnit(servers[0], {"operation": "disable", "user_id": 3})
    assert (unit.ok, unit.http_status) == (True, 200)
    assert jobUnits.serverManagementUnit(servers[0], {"operation": "disable"}).summary == "A user ID is required"
    assert jobUnits.serverManagementUnit(servers[0], {"operation": "drop"}).summary == "Unknown operation `drop`"


def test_unknown_kinds():
    from application.models.jobUnits import execute
    assert execute("format_disk", None, {}).summary == "Unknown job kind `format_disk`"


# Single-server writes from the UI are recorded as jobs

def jobsOf(user):
    from application.DBModels import Job
    return Job.query.filter_by(user_id=user.id).order_by(Job.created).all()


def test_a_plugin_action_from_the_server_page_is_recorded(db, fleet, client, auth_headers, monkeypatch):
    import application
    from application.models.plugins import FailPluginResponse
    user, theFleet, servers = fleet

    class Plugin:
        def action(self, server, data):
            return FailPluginResponse({}, ["Server unreachable"])
    monkeypatch.setattr(application, "loadedPlugins", [{"id": "fake", "name": "Fake Plugin",
                                                        "features": {"action": True}, "instance": Plugin(),
                                                        "quickActionMeta": {"quickActionName": "Q"}}])
    response = client.post(f"/plugins/doAction/{servers[0].id}/fake", json={"token": "t0k3n", "state": 1},
                           headers=auth_headers(user))
    assert response.status_code == 200
    assert response.get_json() == {"status": "fail", "data": {}, "error": ["Server unreachable"]}
    [job] = jobsOf(user)
    assert (job.kind, job.title, job.status, job.total, job.failed) == \
        ("plugin_action", "Fake Plugin on misp-0", "failed", 1, 1)
    assert job.params == {"plugin_id": "fake", "data": {"token": "***", "state": 1}}
    assert job.results[0].summary == "Server unreachable"
    assert job.fleet_id == theFleet.id


def test_an_unknown_plugin_is_a_404_and_not_recorded(db, fleet, client, auth_headers, monkeypatch):
    import application
    user, theFleet, servers = fleet
    monkeypatch.setattr(application, "loadedPlugins", [])
    response = client.post(f"/plugins/doAction/{servers[0].id}/nope", json={}, headers=auth_headers(user))
    assert response.status_code == 404 and jobsOf(user) == []


def test_remote_admin_operations_are_recorded_and_their_failures_reported(db, fleet, client, auth_headers,
                                                                         monkeypatch):
    from application.models import serverManagement
    user, theFleet, servers = fleet
    monkeypatch.setattr(serverManagement, "mispPostRequest", lambda *a, **k: FakeResponse(
        403, {"message": "Could not edit the user.", "errors": {"password": ["Too short"]}}, "Forbidden"))
    response = client.post(f"/server-management/user/set-password/{servers[0].id}/7",
                           json={"password": "abc", "confirm_password": "abc"}, headers=auth_headers(user))
    assert response.get_json() == {"error": "Could not edit the user. - password: Too short"}

    monkeypatch.setattr(serverManagement, "mispPostRequest", lambda *a, **k: {
        "AuthKey": {"id": 9, "authkey": "0123456789abcdef0123456789abcdef01234567"}, "_status_code": 200})
    response = client.post(f"/server-management/user/gen-authkey/{servers[0].id}/7", headers=auth_headers(user))
    # The user sees the new key once; the job keeps it redacted
    assert response.get_json()["AuthKey"]["authkey"] == "0123456789abcdef0123456789abcdef01234567"

    setPassword, genAuthkey = jobsOf(user)
    assert (setPassword.kind, setPassword.status, setPassword.title) == \
        ("server_management", "failed", "Set the password of user #7 on misp-0")
    assert setPassword.params == {"operation": "set_password", "user_id": 7,
                                  "payload": {"password": "***", "confirm_password": "***"}}
    assert genAuthkey.status == "done"
    assert genAuthkey.results[0].response["AuthKey"]["authkey"] == "***"


def test_remote_admin_on_someone_elses_server_is_refused_and_not_recorded(db, fleet, make_user, client,
                                                                          auth_headers):
    user, theFleet, servers = fleet
    mallory = make_user(f"mallory-{uuid.uuid4().hex[:6]}@test.test")
    response = client.post(f"/server-management/user/set-password/{servers[0].id}/7", json={},
                           headers=auth_headers(mallory))
    assert response.get_json() == {"error": "Could not set password for user."}
    assert jobsOf(mallory) == [] and jobsOf(user) == []


def test_a_refused_connection_edit_is_reported_and_recorded(db, fleet, client, auth_headers, monkeypatch):
    import application.models.jobUnits as jobUnits
    import application.models.servers as serverModel
    user, theFleet, servers = fleet
    refreshed = []
    monkeypatch.setattr(serverModel, "refreshServerConnectionList", lambda *a: refreshed.append(a) or [])
    monkeypatch.setattr(jobUnits, "mispPostRequest", lambda *a, **k: FakeResponse(
        403, {"name": "You do not have permission", "message": "You do not have permission"}, "Forbidden"))
    response = client.post(f"/servers/editConnection/{servers[0].id}/4",
                           json={"name": "Partner", "authkey": "k" * 40, "push": True}, headers=auth_headers(user))
    assert response.status_code == 502
    assert response.get_json()["message"] == "MISP did not save the change: 403 Forbidden"
    assert refreshed == []

    monkeypatch.setattr(jobUnits, "mispPostRequest", lambda *a, **k: FakeResponse(200, {"Server": {"id": 4}}))
    response = client.post(f"/servers/editConnection/{servers[0].id}/4", json={"name": "Partner", "push": False},
                           headers=auth_headers(user))
    assert response.status_code == 200 and response.get_json()["status_code"] == 200
    assert refreshed == [(servers[0].id, 4)]

    refused, saved = jobsOf(user)
    assert (refused.kind, refused.status, refused.title) == \
        ("edit_connection", "failed", "Edit the sync connection to Partner on misp-0")
    assert refused.params["payload"]["authkey"] == "***"
    assert saved.status == "done"


def test_only_post_rest_queries_are_recorded(db, fleet, client, auth_headers, monkeypatch):
    import application.models.jobUnits as jobUnits
    user, theFleet, servers = fleet
    monkeypatch.setattr(jobUnits, "mispGetRequest", lambda *a, **k: FakeResponse(200, {"version": "3.0.0"}))
    monkeypatch.setattr(jobUnits, "mispPostRequest", lambda *a, **k: FakeResponse(200, {"saved": True}))
    get = client.post(f"/servers/restQuery/{servers[0].id}", json={"method": "GET", "url": "/servers/getVersion",
                                                                   "data": ""}, headers=auth_headers(user))
    assert get.get_json()["data"] == {"version": "3.0.0"}
    assert jobsOf(user) == []
    post = client.post(f"/servers/restQuery/{servers[0].id}", json={"method": "POST", "url": "/events/add",
                                                                    "data": '{"info": "x"}'}, headers=auth_headers(user))
    assert post.get_json()["status_code"] == 200
    [job] = jobsOf(user)
    assert (job.kind, job.status, job.title) == ("rest_query", "done", "POST /events/add on misp-0")
    absolute = client.post(f"/servers/restQuery/{servers[0].id}", json={"method": "GET", "url": "https://x.test/",
                                                                        "data": ""}, headers=auth_headers(user))
    assert "error" in absolute.get_json()


def test_a_failure_to_record_does_not_hide_the_outcome(db, fleet, monkeypatch):
    import application.models.jobRunner as jobRunner
    import application.models.jobs as jobModel
    from application.models.jobs import UnitResult
    user, theFleet, servers = fleet
    monkeypatch.setattr(jobRunner, "execute", lambda kind, server, params: UnitResult(True, summary="Saved"))

    def broken(*a, **k):
        raise RuntimeError("database is locked")
    monkeypatch.setattr(jobModel, "create", broken)
    assert jobRunner.runInline(user, "rest_query", servers[0], {}).summary == "Saved"


# Encryption of the parameters

def test_key_rotation_re_encrypts_job_parameters(app, db, fleet):
    import os
    import application.models.jobs as jobModel
    from application import crypto
    from application.DBModels import Job
    from cryptography.fernet import Fernet
    user, theFleet, servers = fleet
    job = jobModel.create(user, "rest_query", servers[:1], params={"data": {"password": "p"}})
    saved = crypto._cipher
    oldKey, newKey = os.environ["MFC_ENCRYPTION_KEY"], Fernet.generate_key().decode()
    try:
        crypto._cipher = crypto.buildCipher(crypto.parseKeys(f"{newKey},\n{oldKey}"))
        result = app.test_cli_runner().invoke(args=["security", "rotate-key"])
        assert result.exit_code == 0, result.output
        assert "parameters of" in result.output
        db.session.expire_all()
        stored = db.session.get(Job, job.id)
        assert Fernet(newKey).decrypt(stored.params_enc.encode())  # Readable with the new key alone
        assert stored.secret_params == {"data": {"password": "p"}}
    finally:
        # Back on the session's key, for every row the rotation touched
        crypto._cipher = crypto.buildCipher(crypto.parseKeys(f"{oldKey},\n{newKey}"))
        app.test_cli_runner().invoke(args=["security", "rotate-key"])
        crypto._cipher = saved


def test_the_key_check_also_looks_at_job_parameters(app, db, fleet):
    import application
    import application.models.jobs as jobModel
    from application.DBModels import Server
    user, theFleet, servers = fleet
    job = jobModel.create(user, "rest_query", servers[:1], params={"a": 1})
    sample = application.sampleEncryptedAuthkey()
    assert sample is not None  # Servers have keys here; with none, the job's parameters are the sample
    Server.query.update({Server.authkey_enc: None})
    try:
        assert application.sampleEncryptedAuthkey() is not None
    finally:
        db.session.rollback()


# Timeouts of MISP requests

def test_misp_requests_have_a_default_timeout(monkeypatch):
    import application.controllers.utils as utils
    import application.models.setting as settingModel
    utils._readTimeoutCache.update(value=None, read_at=0)
    assert utils.mispTimeout() == (5, 60)
    assert utils.mispTimeout(30) == 30
    monkeypatch.setattr(settingModel, "getRefreshValue", lambda name: 120 if name == "misp_request_timeout" else None)
    utils._readTimeoutCache.update(value=None, read_at=0)
    assert utils.mispTimeout() == (5, 120)
    utils._readTimeoutCache.update(value=None, read_at=0)


@pytest.mark.parametrize("exception, message", [
    (requests.exceptions.ReadTimeout(), "Request timed out"),
    (requests.exceptions.ConnectTimeout(), "Server unreachable"),
    (requests.exceptions.ConnectionError(), "Server unreachable"),
])
def test_timeouts_are_reported(db, fleet, monkeypatch, exception, message):
    import application.controllers.utils as utils
    user, theFleet, servers = fleet
    seen = []

    class Session:
        def mount(self, *a):
            pass

        def get(self, *a, **kwargs):
            seen.append(kwargs.get("timeout"))
            raise exception

        post = get
    monkeypatch.setattr(utils, "getRequestPSession", lambda: Session())
    monkeypatch.setattr(utils, "getMISPRequestSession", lambda: Session())
    monkeypatch.setattr(utils, "mispReadTimeout", lambda: 60)
    assert utils.mispGetRequest(servers[0], "/x", nocache=True) == {"error": message}
    assert utils.mispGetHTMLRequest(servers[0], "/x", nocache=True) == {"error": message}
    assert utils.mispPostRequest(servers[0], "/x") == {"error": message}
    assert seen == [(5, 60)] * 3


def test_new_settings_are_validated():
    import application.models.setting as settingModel
    assert settingModel.getValue("misp_request_timeout") == 60
    assert settingModel.getValue("job_max_concurrency") == 5
    for name, bad in (("misp_request_timeout", 4), ("misp_request_timeout", 601), ("job_max_concurrency", 0),
                      ("job_max_concurrency", 51)):
        with pytest.raises(settingModel.SettingError):
            settingModel.validate(name, bad)


# Migration

def test_migration_adds_and_drops_the_encrypted_parameters(flask_cli):
    columns = ("import sqlite3, os; c = sqlite3.connect(os.environ['SQLALCHEMY_DATABASE_URI']);"
               "print([r[1] for r in c.execute('pragma table_info(jobs)')])")
    flask_cli.upgrade()
    assert "'params_enc'" in flask_cli.python(columns).stdout
    downgraded = flask_cli.run("db", "downgrade", "89f84aee59fc")
    assert downgraded.returncode == 0, downgraded.stderr
    assert "'params_enc'" not in flask_cli.python(columns).stdout
