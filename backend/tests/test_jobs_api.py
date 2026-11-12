"""Jobs API: creating a job on one's own servers, listing and viewing one's jobs, cancelling, retrying"""
import uuid

import pytest


@pytest.fixture()
def owner(db, make_user):
    from application.DBModels import Fleet, Server
    user = make_user(f"api-{uuid.uuid4().hex[:8]}@test.test")
    fleets = []
    for name in ("Alpha", "Beta"):
        fleet = Fleet(name=name, description="", user_id=user.id, timestamp=1)
        db.session.add(fleet)
        fleets.append(fleet)
    db.session.commit()
    servers = []
    for i in range(4):
        server = Server(name=f"api-misp-{i}", url=f"https://api-misp-{i}.test", user_id=user.id,
                        fleet_id=fleets[0 if i < 3 else 1].id)
        server.authkey = f"key-{i}"
        db.session.add(server)
        servers.append(server)
    db.session.commit()
    return user, fleets, servers


@pytest.fixture()
def queued(monkeypatch):
    """Jobs handed to the workers, without running them"""
    from application.workers import tasks
    calls = []
    monkeypatch.setattr(tasks, "runJob", lambda job_id: calls.append(job_id))
    return calls


@pytest.fixture()
def plugins(monkeypatch):
    import application
    from application.models.plugins import SuccessPluginResponse

    class Plugin:
        def action(self, server, data):
            return SuccessPluginResponse({"message": "ok"})

        def quickAction(self, server, data):
            return SuccessPluginResponse({"message": "quick"})
    monkeypatch.setattr(application, "loadedPlugins", [
        {"id": "live-mode", "name": "Live Mode", "features": {"action": True, "quickAction": True},
         "instance": Plugin(), "quickActionMeta": {"quickActionName": "Enable live"}},
        {"id": "viewer", "name": "Viewer", "features": {"action": False, "quickAction": False},
         "instance": Plugin(), "quickActionMeta": {"quickActionName": "-"}},
    ])


def post(client, headers, path, body=None):
    return client.post(path, json=body if body is not None else {}, headers=headers)


# Creating

def test_create_a_plugin_job(db, client, auth_headers, owner, queued, plugins):
    user, fleets, servers = owner
    ids = [s.id for s in servers[:3]]
    response = post(client, auth_headers(user), "/jobs", {
        "kind": "plugin_action", "server_ids": ids + [ids[0]],
        "params": {"plugin_id": "live-mode", "data": {"state": "1", "password": "s"}}})
    assert response.status_code == 202, response.get_json()
    body = response.get_json()
    job = body["job"]
    assert queued == [body["job_id"]] == [job["id"]]
    assert (job["kind"], job["status"], job["total"], job["done"], job["title"]) == \
        ("plugin_action", "queued", 3, 0, "Live Mode on 3 servers")
    assert job["fleet_id"] == fleets[0].id and job["fleet_name"] == "Alpha"
    assert [r["server_id"] for r in job["results"]] == ids
    assert {r["status"] for r in job["results"]} == {"pending"}
    assert job["params"] == {"plugin_id": "live-mode", "data": {"state": "1", "password": "***"}}
    assert "params_enc" not in job


def test_titles_and_fleets(db, client, auth_headers, owner, queued, plugins):
    user, fleets, servers = owner
    headers = auth_headers(user)
    one = post(client, headers, "/jobs", {"kind": "plugin_quick_action", "server_ids": [servers[0].id],
                                          "params": {"plugin_id": "live-mode"}}).get_json()["job"]
    assert one["title"] == "Enable live on api-misp-0"
    mixed = post(client, headers, "/jobs", {"kind": "rest_query", "server_ids": [servers[0].id, servers[3].id],
                                            "params": {"method": "post", "url": " /events/index ", "data": "{}"},
                                            "title": "  My query  "}).get_json()["job"]
    assert (mixed["title"], mixed["fleet_id"], mixed["fleet_name"]) == ("My query", None, "")
    assert mixed["params"] == {"method": "POST", "url": "/events/index", "data": "{}"}
    default = post(client, headers, "/jobs", {"kind": "rest_query", "server_ids": [servers[0].id, servers[1].id],
                                              "params": {"url": "/servers/getVersion"}}).get_json()["job"]
    assert default["title"] == "GET /servers/getVersion on 2 servers"


@pytest.mark.parametrize("body, status, message", [
    ({"kind": "server_management", "server_ids": [0], "params": {}}, 400, "`kind` must be one of"),
    ({"kind": "rest_query", "server_ids": [], "params": {"url": "/x"}}, 400, "non-empty list"),
    ({"kind": "rest_query", "server_ids": ["1"], "params": {"url": "/x"}}, 400, "non-empty list"),
    ({"kind": "rest_query", "server_ids": [True], "params": {"url": "/x"}}, 400, "non-empty list"),
    ({"kind": "rest_query", "server_ids": "SERVERS", "params": {"url": "https://x.test/"}}, 400, "path on the MISP server"),
    ({"kind": "rest_query", "server_ids": "SERVERS", "params": {"url": "/x", "method": "DELETE"}}, 400, "GET or POST"),
    ({"kind": "rest_query", "server_ids": "SERVERS", "params": "nope"}, 400, "must be an object"),
    ({"kind": "plugin_action", "server_ids": "SERVERS", "params": {"plugin_id": "nope"}}, 400, "Unknown plugin"),
    ({"kind": "plugin_action", "server_ids": "SERVERS", "params": {"plugin_id": "viewer"}}, 400, "has no action"),
    ({"kind": "plugin_action", "server_ids": "SERVERS", "params": {"plugin_id": "live-mode", "data": [1]}}, 400, "`params.data`"),
    ({"kind": "rest_query", "server_ids": "SERVERS", "params": {"url": "/x"}, "title": 3}, 400, "`title`"),
])
def test_invalid_jobs_are_refused(db, client, auth_headers, owner, queued, plugins, body, status, message):
    user, fleets, servers = owner
    if body["server_ids"] == "SERVERS":
        body = dict(body, server_ids=[servers[0].id])
    response = post(client, auth_headers(user), "/jobs", body)
    assert response.status_code == status
    assert message in response.get_json()["message"]
    assert queued == []


def test_jobs_on_someone_elses_servers_are_refused(db, client, auth_headers, owner, make_user, queued):
    user, fleets, servers = owner
    mallory = make_user(f"mallory-{uuid.uuid4().hex[:6]}@test.test")
    response = post(client, auth_headers(mallory), "/jobs", {
        "kind": "rest_query", "server_ids": [servers[0].id], "params": {"url": "/servers/getVersion"}})
    assert response.status_code == 404
    assert response.get_json()["message"] == f"Unknown server: {servers[0].id}"
    assert queued == []
    # Mixing one's own server with someone else's is refused as a whole
    from application.DBModels import Fleet, Server
    fleet = Fleet(name="M", description="", user_id=mallory.id, timestamp=1)
    db.session.add(fleet)
    db.session.commit()
    own = Server(name="m", url="https://m.test", user_id=mallory.id, fleet_id=fleet.id)
    db.session.add(own)
    db.session.commit()
    response = post(client, auth_headers(mallory), "/jobs", {
        "kind": "rest_query", "server_ids": [own.id, servers[1].id], "params": {"url": "/x"}})
    assert response.status_code == 404 and queued == []


def test_unreachable_workers_fail_the_job_at_once(db, client, auth_headers, owner, monkeypatch):
    from application.DBModels import Job
    from application.workers import tasks
    user, fleets, servers = owner

    def down(job_id):
        raise ConnectionError("redis down")
    monkeypatch.setattr(tasks, "runJob", down)
    response = post(client, auth_headers(user), "/jobs", {
        "kind": "rest_query", "server_ids": [servers[0].id, servers[1].id], "params": {"url": "/x"}})
    assert response.status_code == 503
    job = Job.query.filter_by(user_id=user.id).one()
    assert (job.status, job.failed) == ("failed", 2)
    assert {r.summary for r in job.results} == {"Not started: the workers could not be reached"}


def test_unauthenticated_requests_are_refused(client):
    assert client.post("/jobs", json={}).status_code == 401
    assert client.get("/jobs").status_code == 401


# Listing and viewing

def makeJob(user, servers, kind="rest_query", status=None, created=None, fleet=None, results=None):
    import application.models.jobs as jobModel
    job = jobModel.create(user, kind, servers, params={"url": "/x", "authkey": "k"}, title=f"{kind} job", fleet=fleet)
    for row, outcome in zip(job.results, results or []):
        jobModel.recordResult(row, outcome)
    if status is not None:
        job.status = status
    if created is not None:
        job.created = created
    from application import db
    db.session.commit()
    return job


def test_list_jobs_newest_first_with_filters_and_pages(db, client, auth_headers, owner, make_user):
    user, fleets, servers = owner
    other = make_user(f"other-{uuid.uuid4().hex[:6]}@test.test")
    makeJob(other, [], created=5000)
    a = makeJob(user, servers[:2], status="done", created=1000, fleet=fleets[0], results=["ok", "ok"])
    b = makeJob(user, servers[3:], kind="plugin_action", status="failed", created=2000, fleet=fleets[1], results=["error"])
    c = makeJob(user, servers[:3], status="running", created=3000, fleet=fleets[0], results=["ok"])
    headers = auth_headers(user)

    def ids(query=""):
        response = client.get(f"/jobs{query}", headers=headers)
        assert response.status_code == 200, response.get_json()
        return [job["id"] for job in response.get_json()["jobs"]]
    assert ids() == [c.id, b.id, a.id]
    assert ids(f"?fleet_id={fleets[0].id}") == [c.id, a.id]
    assert ids("?status=done,failed") == [b.id, a.id]
    assert ids("?kind=plugin_action") == [b.id]
    assert ids(f"?server_id={servers[3].id}") == [b.id]
    page = client.get("/jobs?limit=2&page=2", headers=headers).get_json()
    assert (page["total"], page["page"], page["limit"], [j["id"] for j in page["jobs"]]) == (3, 2, 2, [a.id])
    first = client.get("/jobs?limit=1", headers=headers).get_json()["jobs"][0]
    assert (first["done"], first["total"]) == (1, 3)
    assert "results" not in first and first["params"]["authkey"] == "***"


@pytest.mark.parametrize("query, message", [
    ("?status=great", "Unknown `status`"), ("?kind=x", "Unknown `kind`"), ("?page=0", "`page`"),
    ("?limit=101", "`limit`"), ("?fleet_id=a", "`fleet_id` must be an integer"),
])
def test_invalid_list_filters(db, client, auth_headers, owner, query, message):
    user, fleets, servers = owner
    response = client.get(f"/jobs{query}", headers=auth_headers(user))
    assert response.status_code == 400 and message in response.get_json()["message"]


def test_view_a_job(db, client, auth_headers, owner, make_user):
    user, fleets, servers = owner
    job = makeJob(user, servers[:2], status="partial", results=["ok", "error"])
    response = client.get(f"/jobs/{job.id}", headers=auth_headers(user))
    assert response.status_code == 200
    body = response.get_json()
    assert [r["status"] for r in body["results"]] == ["ok", "error"] and body["done"] == 2
    mallory = make_user(f"mallory-{uuid.uuid4().hex[:6]}@test.test")
    assert client.get(f"/jobs/{job.id}", headers=auth_headers(mallory)).status_code == 404
    assert client.get("/jobs/not-a-job", headers=auth_headers(user)).status_code == 404


# Cancelling

def test_cancel_a_running_job(db, client, auth_headers, owner, make_user):
    import application.models.jobRunner as jobRunner
    user, fleets, servers = owner
    job = makeJob(user, servers[:2], status="running")
    mallory = make_user(f"mallory-{uuid.uuid4().hex[:6]}@test.test")
    assert post(client, auth_headers(mallory), f"/jobs/{job.id}/cancel").status_code == 404
    assert not jobRunner.cancelRequested(job.id)
    response = post(client, auth_headers(user), f"/jobs/{job.id}/cancel")
    assert response.status_code == 202 and response.get_json()["cancel_requested"] is True
    assert jobRunner.cancelRequested(job.id)
    jobRunner.clearCancel(job.id)


def test_a_finished_job_cannot_be_cancelled(db, client, auth_headers, owner):
    user, fleets, servers = owner
    job = makeJob(user, servers[:1], status="done", results=["ok"])
    response = post(client, auth_headers(user), f"/jobs/{job.id}/cancel")
    assert response.status_code == 409


def test_a_cancelled_queued_job_runs_nothing(db, client, auth_headers, owner, monkeypatch):
    import application.models.jobRunner as jobRunner
    user, fleets, servers = owner
    ran = []
    monkeypatch.setattr(jobRunner, "execute", lambda *a: ran.append(a))
    job = makeJob(user, servers[:3])
    post(client, auth_headers(user), f"/jobs/{job.id}/cancel")
    jobRunner.run(job.id)
    assert ran == [] and job.status == "cancelled"
    assert {r.status for r in job.results} == {"cancelled"}


# Retrying

def test_retry_the_failed_servers(db, client, auth_headers, owner, queued):
    from application.DBModels import Job
    user, fleets, servers = owner
    job = makeJob(user, servers[:3], status="partial", fleet=fleets[0], results=["ok", "error", "error"])
    response = post(client, auth_headers(user), f"/jobs/{job.id}/retry", {"only_failed": True})
    assert response.status_code == 202, response.get_json()
    retried = response.get_json()["job"]
    assert [r["server_id"] for r in retried["results"]] == [servers[1].id, servers[2].id]
    assert (retried["title"], retried["kind"], retried["fleet_id"]) == ("Retry: rest_query job", "rest_query", fleets[0].id)
    assert queued == [retried["id"]]
    # The real parameters, not the redacted copy
    assert Job.query.get(retried["id"]).secret_params == {"url": "/x", "authkey": "k"}
    # Retrying a retry does not stack prefixes; all servers when asked
    again = post(client, auth_headers(user), f"/jobs/{retried['id']}/retry", {"only_failed": False})
    assert again.status_code == 409  # Still queued
    Job.query.get(retried["id"]).status = "failed"
    db.session.commit()
    again = post(client, auth_headers(user), f"/jobs/{retried['id']}/retry", {"only_failed": False}).get_json()["job"]
    assert again["title"] == "Retry: rest_query job" and again["total"] == 2


def test_retry_skips_deleted_servers_and_needs_something_to_retry(db, client, auth_headers, owner, queued):
    user, fleets, servers = owner
    job = makeJob(user, servers[:2], status="failed", results=["error", "error"])
    db.session.delete(servers[1])
    db.session.commit()
    retried = post(client, auth_headers(user), f"/jobs/{job.id}/retry").get_json()["job"]
    assert [r["server_id"] for r in retried["results"]] == [servers[0].id]
    done = makeJob(user, servers[:1], status="done", results=["ok"])
    response = post(client, auth_headers(user), f"/jobs/{done.id}/retry")
    assert response.status_code == 409 and response.get_json()["message"] == "No server left to retry"


def test_jobs_api_end_to_end(db, client, auth_headers, owner, monkeypatch, plugins):
    """Create → the worker runs it → view: what the batch modal does"""
    import application.models.jobRunner as jobRunner
    from application.workers import tasks
    user, fleets, servers = owner
    monkeypatch.setattr(tasks, "runJob", lambda job_id: jobRunner.run(job_id))
    response = post(client, auth_headers(user), "/jobs", {
        "kind": "plugin_quick_action", "server_ids": [s.id for s in servers[:2]], "params": {"plugin_id": "live-mode"}})
    job_id = response.get_json()["job_id"]
    body = client.get(f"/jobs/{job_id}", headers=auth_headers(user)).get_json()
    assert (body["status"], body["succeeded"], body["done"]) == ("done", 2, 2)
    assert {r["summary"] for r in body["results"]} == {"quick"}
