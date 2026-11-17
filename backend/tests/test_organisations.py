"""Organisations of a MISP server (Remote administration): listing and its cache, comparison with the rest of the
fleet, add / edit through one-server jobs, and the job creating an organisation on other servers"""
import pytest

from test_plugin_failures import Answer, UNREACHABLE

UUID_CIRCL = "55f6ea5e-2c60-40e5-964f-47a8950d210f"
UUID_ADMIN = "5c1a1b2c-0000-4000-8000-000000000001"
UUID_ACME = "5c1a1b2c-0000-4000-8000-000000000002"
UUID_OTHER = "5c1a1b2c-0000-4000-8000-000000000099"


def org(id, uuid, name, local=True, **fields):
    return {"Organisation": {"id": str(id), "uuid": uuid, "name": name, "local": local, **fields}}


def parsed(*entries):
    """Index entries as the model gets them (unwrapped), compacted"""
    from application.models import organisations
    return organisations.parse([entry["Organisation"] for entry in entries])


@pytest.fixture(autouse=True)
def _app(app):
    """Models are imported once the app (and its fake Redis) exists"""
    return app


@pytest.fixture()
def ops():
    from application.models import mispOps
    return mispOps


@pytest.fixture()
def model():
    from application.models import organisations
    return organisations


@pytest.fixture()
def fleet(db, make_user):
    """Three servers of one fleet, and one server of another fleet of the same user"""
    from application.DBModels import Fleet, Server
    user = make_user("organisations@test.local")
    fleets = [Fleet(name=name, description="", user_id=user.id, timestamp=1) for name in ("orgs", "orgs other")]
    db.session.add_all(fleets)
    db.session.commit()
    servers = [Server(name=name, url=f"https://{name}.test", authkey="K" * 40, fleet_id=fleets[0].id, user_id=user.id)
               for name in ("misp-a", "misp-b", "misp-c")]
    servers.append(Server(name="misp-z", url="https://misp-z.test", authkey="K" * 40, fleet_id=fleets[1].id,
                          user_id=user.id))
    db.session.add_all(servers)
    db.session.commit()
    yield {"user": user, "servers": servers, "fleets": fleets}
    from application.DBModels import Job
    for job in Job.query.filter_by(user_id=user.id).all():
        db.session.delete(job)
    for server in servers:
        db.session.delete(server)
    for item in fleets:
        db.session.delete(item)
    db.session.commit()


@pytest.fixture()
def misp(monkeypatch, ops):
    """MISP answers by server name and path; POSTs are recorded"""
    answers, posted = {}, []

    def fakeGet(server, url, *args, **kwargs):
        answer = answers.get((server.name, url), UNREACHABLE)
        return answer() if callable(answer) else answer

    def fakePost(server, url, data=None, *args, **kwargs):
        posted.append((server.name, url, data))
        answer = answers.get((server.name, "POST " + url), Answer(200, {"saved": True}))
        return answer(data) if callable(answer) else answer
    monkeypatch.setattr(ops, "mispGetRequest", fakeGet)
    monkeypatch.setattr(ops, "mispPostRequest", fakePost)
    return {"answers": answers, "posted": posted}


INDEX = "/organisations/index/scope:all"


def listing(*records):
    return Answer(200, list(records))


# Records

def test_records_are_compacted_sorted_and_keyed_by_lowercase_uuid(model):
    organisations = parsed(
        org(9, UUID_CIRCL.upper(), "CIRCL", restricted_to_domain=["circl.lu", " "], user_count="4", sector="CERT"),
        org(1, UUID_ADMIN, "ADMIN", restricted_to_domain='["admin.test"]'),
        org(2, UUID_ACME, "acme", local=False, restricted_to_domain="a.test\nb.test"),
        {"Organisation": {"id": "3", "name": "No UUID"}},
    )
    assert [o["name"] for o in organisations] == ["acme", "ADMIN", "CIRCL"]
    circl = organisations[2]
    assert circl["uuid"] == UUID_CIRCL and circl["id"] == 9 and circl["local"] is True
    assert circl["restricted_to_domain"] == ["circl.lu"] and circl["user_count"] == 4 and circl["sector"] == "CERT"
    assert organisations[1]["restricted_to_domain"] == ["admin.test"] and organisations[1]["user_count"] is None
    assert organisations[0]["restricted_to_domain"] == ["a.test", "b.test"] and organisations[0]["local"] is False


def test_comparison_by_uuid_then_name(model):
    own = parsed(org(1, UUID_CIRCL, "CIRCL"), org(2, UUID_ACME, "Acme  Corp"), org(3, UUID_ADMIN, "ADMIN"))
    others = {
        10: parsed(org(5, UUID_CIRCL, "circl"), org(6, UUID_OTHER, "acme corp")),
        11: parsed(org(7, UUID_CIRCL, "CIRCL Luxembourg"), org(8, UUID_ACME, "Acme Corp")),
        12: [],
    }
    result = model.compare(own, others)
    assert result[UUID_CIRCL] == {"same": [10], "renamed": [[11, "CIRCL Luxembourg"]], "other_uuid": []}
    assert result[UUID_ACME] == {"same": [11], "renamed": [], "other_uuid": [[10, UUID_OTHER]]}
    assert result[UUID_ADMIN] == {"same": [], "renamed": [], "other_uuid": []}


# Listing

def test_listing_is_cached_until_refreshed(fleet, misp, model):
    server = fleet["servers"][0]
    calls = []
    misp["answers"][("misp-a", INDEX)] = lambda: calls.append(1) or listing(org(1, UUID_CIRCL, "CIRCL"))
    first = model.organisationsOf(server)
    assert first["cached"] is False and [o["name"] for o in first["organisations"]] == ["CIRCL"]
    assert model.organisationsOf(server)["cached"] is True
    assert model.organisationsOf(server, refresh=True)["cached"] is False
    assert len(calls) == 2


def test_failures_are_not_cached(fleet, misp, model, ops):
    server = fleet["servers"][0]
    misp["answers"][("misp-a", INDEX)] = Answer(403, {"message": "Not allowed"})
    with pytest.raises(ops.MispOpError, match="Not allowed"):
        model.organisationsOf(server)
    assert model.readCached(server) is None


def test_index_endpoint(client, auth_headers, fleet, misp, make_user):
    server = fleet["servers"][0]
    misp["answers"][("misp-a", INDEX)] = listing(org(1, UUID_CIRCL, "CIRCL", user_count=2))
    response = client.get(f"/server-management/organisations/{server.id}", headers=auth_headers(fleet["user"]))
    assert response.status_code == 200
    body = response.get_json()
    assert body["server_id"] == server.id and body["cached"] is False and isinstance(body["fetched_at"], int)
    assert body["organisations"][0]["name"] == "CIRCL" and body["organisations"][0]["user_count"] == 2
    other = make_user("organisations-other@test.local")
    assert client.get(f"/server-management/organisations/{server.id}",
                      headers=auth_headers(other)).status_code == 404


def test_index_endpoint_reports_misp_failures(client, auth_headers, fleet, misp):
    server = fleet["servers"][0]
    response = client.get(f"/server-management/organisations/{server.id}?refresh=1",
                          headers=auth_headers(fleet["user"]))
    assert response.status_code == 502
    assert "Server unreachable" in response.get_json()["message"]


# Fleet comparison

def test_fleet_comparison(client, auth_headers, fleet, misp, model, monkeypatch):
    import application.models.utils as utils
    a, b, c, z = fleet["servers"]
    misp["answers"][("misp-a", INDEX)] = listing(org(1, UUID_CIRCL, "CIRCL"), org(2, UUID_ACME, "Acme"))
    model.store(b, parsed(org(4, UUID_CIRCL, "CIRCL")), now=1000)
    fetched = []

    async def fakeFetcher(server, urls, timeout=None):
        fetched.append((server.name, urls, timeout))
        return [UNREACHABLE]
    monkeypatch.setattr(utils, "asyncFetcher", fakeFetcher)
    response = client.get(f"/server-management/organisations/{a.id}/fleet", headers=auth_headers(fleet["user"]))
    assert response.status_code == 200
    body = response.get_json()
    # b from its cached list, c could not be listed (never "missing"), z is in another fleet
    assert fetched == [("misp-c", [INDEX], model.FLEET_TIMEOUT)]
    assert body["compared"] == [{"id": b.id, "name": "misp-b", "fetched_at": 1000}]
    assert body["unavailable"] == [{"id": c.id, "name": "misp-c",
                                    "error": "Server unreachable"}]
    assert body["organisations"][UUID_CIRCL] == {"same": [b.id], "renamed": [], "other_uuid": []}
    assert body["organisations"][UUID_ACME] == {"same": [], "renamed": [], "other_uuid": []}


def test_fleet_comparison_reads_lists_again_on_refresh(client, auth_headers, fleet, misp, model, monkeypatch):
    import application.models.utils as utils
    a, b, c, _ = fleet["servers"]
    misp["answers"][("misp-a", INDEX)] = listing(org(1, UUID_CIRCL, "CIRCL"))
    model.store(b, parsed(org(4, UUID_CIRCL, "CIRCL")))

    async def fakeFetcher(server, urls, timeout=None):
        return [[org(8, UUID_OTHER, "circl")]]
    monkeypatch.setattr(utils, "asyncFetcher", fakeFetcher)
    body = client.get(f"/server-management/organisations/{a.id}/fleet?refresh=1",
                      headers=auth_headers(fleet["user"])).get_json()
    assert body["unavailable"] == []
    assert body["organisations"][UUID_CIRCL]["other_uuid"] == [[b.id, UUID_OTHER], [c.id, UUID_OTHER]]
    # The lists read are cached for the next look
    assert model.readCached(c)["organisations"][0]["uuid"] == UUID_OTHER


def test_server_alone_in_its_fleet_compares_with_nothing(fleet, misp, model):
    z = fleet["servers"][3]
    misp["answers"][("misp-z", INDEX)] = listing(org(1, UUID_CIRCL, "CIRCL"))
    result = model.fleetComparison(z)
    assert result["compared"] == [] and result["unavailable"] == []
    assert result["organisations"] == {UUID_CIRCL: {"same": [], "renamed": [], "other_uuid": []}}


# Add / edit

def test_add_organisation(client, auth_headers, fleet, misp, model):
    from application.DBModels import Job
    a = fleet["servers"][0]
    model.store(a, [])
    misp["answers"][("misp-a", "POST /admin/organisations/add")] = lambda data: Answer(200, {"Organisation": {
        "id": "12", **data["Organisation"], "uuid": UUID_ACME, "restricted_to_domain": ["acme.test", "acme.example"]}})
    response = client.post(f"/server-management/organisations/{a.id}/add", headers=auth_headers(fleet["user"]), json={
        "name": " Acme ", "local": False, "sector": "Energy", "restricted_to_domain": "acme.test\n\nacme.example"})
    assert response.status_code == 200
    created = response.get_json()["Organisation"]
    assert created["id"] == 12 and created["name"] == "Acme" and created["local"] is False
    assert misp["posted"] == [("misp-a", "/admin/organisations/add", {"Organisation": {
        "name": "Acme", "local": False, "sector": "Energy", "restricted_to_domain": "acme.test\nacme.example"}})]
    # The cached list is dropped, and the change is in the audit log
    assert model.readCached(a) is None
    job = Job.query.filter_by(user_id=fleet["user"].id).one()
    assert job.kind == "server_management" and job.title == "Add organisation Acme on misp-a"
    assert job.status == "done"


@pytest.mark.parametrize("payload, field", [
    ({"local": True}, "name"),
    ({"name": "  "}, "name"),
    ({"name": "Acme", "uuid": "not-a-uuid"}, "uuid"),
    ({"name": "Acme", "local": "yes"}, "local"),
    ({"name": "Acme", "created_by": 1}, "created_by"),
    ({"name": "Acme", "restricted_to_domain": ["a b.test"]}, "restricted_to_domain"),
])
def test_add_refuses_bad_input(client, auth_headers, fleet, misp, payload, field):
    a = fleet["servers"][0]
    response = client.post(f"/server-management/organisations/{a.id}/add", headers=auth_headers(fleet["user"]),
                           json=payload)
    assert response.status_code == 400 and response.get_json()["field"] == field
    assert misp["posted"] == []


def test_add_reports_misp_refusal(client, auth_headers, fleet, misp):
    a = fleet["servers"][0]
    misp["answers"][("misp-a", "POST /admin/organisations/add")] = Answer(
        403, {"name": "Could not add Organisation", "message": "Could not add Organisation",
              "errors": {"name": ["An organisation with this name already exists."]}})
    response = client.post(f"/server-management/organisations/{a.id}/add", headers=auth_headers(fleet["user"]),
                           json={"name": "CIRCL"})
    assert response.status_code == 502
    assert "An organisation with this name already exists." in response.get_json()["message"]


def test_edit_sends_only_the_changes(client, auth_headers, fleet, misp):
    a = fleet["servers"][0]
    response = client.post(f"/server-management/organisations/{a.id}/edit/9", headers=auth_headers(fleet["user"]),
                           json={"nationality": "Luxembourg", "restricted_to_domain": []})
    assert response.status_code == 200
    assert misp["posted"] == [("misp-a", "/admin/organisations/edit/9",
                               {"Organisation": {"nationality": "Luxembourg", "restricted_to_domain": ""}})]


@pytest.mark.parametrize("payload", [{}, {"uuid": ""}, {"name": ""}])
def test_edit_refuses_empty_changes(client, auth_headers, fleet, misp, payload):
    a = fleet["servers"][0]
    response = client.post(f"/server-management/organisations/{a.id}/edit/9", headers=auth_headers(fleet["user"]),
                           json=payload)
    assert response.status_code == 400 and misp["posted"] == []


def test_writes_on_another_users_server_are_not_found(client, auth_headers, fleet, misp, make_user):
    a = fleet["servers"][0]
    other = make_user("organisations-intruder@test.local")
    for url, body in ((f"/server-management/organisations/{a.id}/add", {"name": "X"}),
                      (f"/server-management/organisations/{a.id}/edit/1", {"name": "X"}),
                      (f"/server-management/organisations/{a.id}/copy",
                       {"uuid": UUID_CIRCL, "server_ids": [fleet["servers"][1].id]})):
        assert client.post(url, headers=auth_headers(other), json=body).status_code == 404
    assert misp["posted"] == []


# Copy to other servers

@pytest.fixture()
def queued(monkeypatch):
    from application.workers import tasks
    calls = []
    monkeypatch.setattr(tasks, "runJob", lambda job_id: calls.append(job_id))
    return calls


def test_copy_starts_a_job_on_the_chosen_servers(client, auth_headers, fleet, misp, model, queued):
    from application.DBModels import Job
    a, b, c, _ = fleet["servers"]
    misp["answers"][("misp-a", INDEX)] = listing(org(1, UUID_CIRCL, "CIRCL", sector="CERT", contacts="cert@circl.lu",
                                                     restricted_to_domain=["circl.lu"]))
    response = client.post(f"/server-management/organisations/{a.id}/copy", headers=auth_headers(fleet["user"]),
                           json={"uuid": UUID_CIRCL.upper(), "server_ids": [c.id, b.id, c.id]})
    assert response.status_code == 202
    body = response.get_json()
    assert queued == [body["job_id"]]
    job = Job.query.get(body["job_id"])
    assert job.kind == "organisation_copy" and job.title == "Create organisation CIRCL on 2 servers"
    assert [result.server_id for result in job.results] == [b.id, c.id]
    assert job.secret_params == {"organisation": {"uuid": UUID_CIRCL, "name": "CIRCL", "type": "", "nationality": "",
                                                  "sector": "CERT", "description": "", "contacts": "cert@circl.lu"},
                                 "local": False}


@pytest.mark.parametrize("body, status, field", [
    ({"uuid": UUID_CIRCL, "server_ids": []}, 400, "server_ids"),
    ({"uuid": UUID_CIRCL, "server_ids": ["two"]}, 400, "server_ids"),
    ({"uuid": "nope", "server_ids": ["B"]}, 400, "uuid"),
    ({"uuid": UUID_CIRCL, "server_ids": ["A"]}, 400, "server_ids"),
    ({"uuid": UUID_CIRCL, "server_ids": ["Z"]}, 400, "server_ids"),
    ({"uuid": UUID_CIRCL, "server_ids": [999999]}, 404, None),
    ({"uuid": UUID_OTHER, "server_ids": ["B"]}, 404, "uuid"),
    ({"uuid": UUID_CIRCL, "server_ids": ["B"], "local": "yes"}, 400, "local"),
])
def test_copy_refuses_bad_input(client, auth_headers, fleet, misp, queued, body, status, field):
    a, b, _, z = fleet["servers"]
    named = {"A": a.id, "B": b.id, "Z": z.id}
    body = dict(body, server_ids=[named.get(id, id) if isinstance(id, str) else id for id in body["server_ids"]])
    misp["answers"][("misp-a", INDEX)] = listing(org(1, UUID_CIRCL, "CIRCL"))
    response = client.post(f"/server-management/organisations/{a.id}/copy", headers=auth_headers(fleet["user"]),
                           json=body)
    assert response.status_code == status
    if field:
        assert response.get_json()["field"] == field
    assert queued == []


COPY = {"organisation": {"uuid": UUID_CIRCL, "name": "CIRCL", "type": "CSIRT", "nationality": "", "sector": "CERT",
                         "description": "", "contacts": ""}, "local": False}


def test_copy_unit_creates_the_organisation(fleet, misp, model):
    b = fleet["servers"][1]
    misp["answers"][("misp-b", INDEX)] = listing(org(1, UUID_ADMIN, "ADMIN"))
    misp["answers"][("misp-b", "POST /admin/organisations/add")] = lambda data: Answer(
        200, {"Organisation": {"id": "30", **data["Organisation"]}})
    unit = model.copyUnit(b, COPY)
    assert unit.ok and unit.summary == "Created" and unit.response["created"] is True
    assert misp["posted"] == [("misp-b", "/admin/organisations/add", {"Organisation": {
        "uuid": UUID_CIRCL, "name": "CIRCL", "local": False, "type": "CSIRT", "sector": "CERT"}})]
    assert model.readCached(b) is None


def test_copy_unit_creates_a_local_organisation_when_asked(fleet, misp, model):
    b = fleet["servers"][1]
    misp["answers"][("misp-b", INDEX)] = listing()
    unit = model.copyUnit(b, dict(COPY, local=True))
    assert unit.ok and unit.summary == "Created (local)"
    assert misp["posted"][0][2]["Organisation"]["local"] is True


@pytest.mark.parametrize("theirs, ok, summary", [
    (org(4, UUID_CIRCL, "circl"), True, "Already there"),
    (org(4, UUID_CIRCL, "CIRCL Luxembourg"), True, "Already there, named `CIRCL Luxembourg` (left as it is)"),
    (org(4, UUID_OTHER, "Circl"), False, f"`Circl` already exists here with another UUID ({UUID_OTHER})"),
])
def test_copy_unit_never_duplicates(fleet, misp, model, theirs, ok, summary):
    b = fleet["servers"][1]
    misp["answers"][("misp-b", INDEX)] = listing(theirs)
    unit = model.copyUnit(b, COPY)
    assert unit.ok is ok and unit.summary == summary and misp["posted"] == []


def test_copy_unit_reports_failures(fleet, misp, model):
    b = fleet["servers"][1]
    unit = model.copyUnit(b, COPY)
    assert not unit.ok and unit.summary == "Could not list the organisations: Server unreachable"
    misp["answers"][("misp-b", INDEX)] = listing()
    misp["answers"][("misp-b", "POST /admin/organisations/add")] = Answer(403, {"message": "Forbidden"})
    unit = model.copyUnit(b, COPY)
    assert not unit.ok and unit.http_status == 403
    assert unit.summary.startswith("Could not create organisation `CIRCL`: HTTP 403")


def test_copy_runs_as_a_job(app, fleet, misp, model):
    """The unit wired into the job runner, end to end on two servers"""
    import application.models.jobRunner as jobRunner
    import application.models.jobs as jobModel
    _, b, c, _ = fleet["servers"]
    misp["answers"][("misp-b", INDEX)] = listing()
    misp["answers"][("misp-c", INDEX)] = listing(org(4, UUID_CIRCL, "CIRCL"))
    job = jobModel.create(fleet["user"], "organisation_copy", [b, c], params=COPY, title="copy")
    job = jobRunner.run(job.id, max_concurrency=1)
    assert job.status == "done" and job.succeeded == 2
    assert sorted(result.summary for result in job.results) == ["Already there", "Created"]
