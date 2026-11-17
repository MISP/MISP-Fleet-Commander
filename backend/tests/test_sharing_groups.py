"""Sharing groups of a MISP server (Remote administration): listing and its cache, comparison with the rest of the
fleet, add / edit / delete through one-server jobs, and the job creating a group on other servers"""
import pytest

from test_plugin_failures import Answer, UNREACHABLE

SG = "5c1a1b2c-0000-4000-8000-0000000000a1"
SG_BETA = "5c1a1b2c-0000-4000-8000-0000000000a2"
UUID_ADMIN = "5c1a1b2c-0000-4000-8000-000000000001"
UUID_ACME = "5c1a1b2c-0000-4000-8000-000000000002"
UUID_CIRCL = "55f6ea5e-2c60-40e5-964f-47a8950d210f"
UUID_OTHER = "5c1a1b2c-0000-4000-8000-000000000099"

INDEX = "/sharing_groups/index"
PASSIVE = "/sharing_groups/index/true"
ORG_INDEX = "/organisations/index/scope:all"
BASEURL = "/servers/getSetting/MISP.baseurl"

ADMIN = (1, UUID_ADMIN, "ADMIN", True)
ACME = (2, UUID_ACME, "Acme", False)
CIRCL = (3, UUID_CIRCL, "CIRCL", False)


class Counted(Answer):
    """An answer carrying `X-Result-Count`"""

    def __init__(self, count):
        super().__init__(200, [])
        if count is not None:
            self.headers = {"X-Result-Count": str(count)}


def sg(id, uuid, name, members=(), servers=(), *, rows=None, **attributes):
    """An index entry as MISP 3.0 answers it. members: (org id, uuid, name, extend); servers: (id, name, all_orgs)"""
    group = {"id": str(id), "uuid": uuid, "name": name, "description": "", "releasability": "", "local": False,
             "active": True, "roaming": False, "org_count": str(len(members)), **attributes}
    orgs = [{"id": str(100 + i), "sharing_group_id": str(id), "org_id": str(m[0]), "extend": m[3],
             "Organisation": {"name": m[2], "id": str(m[0]), "uuid": m[1]}} for i, m in enumerate(members)]
    remote = [{"all_orgs": s[2], "server_id": str(s[0]), "sharing_group_id": str(id),
               "Server": [] if s[0] == 0 else {"id": str(s[0]), "name": s[1]}} for s in servers]
    return {"SharingGroup": group, "Organisation": {"id": "1", "name": "ADMIN", "uuid": UUID_ADMIN},
            "SharingGroupOrg": orgs if rows is None else rows, "SharingGroupServer": remote,
            "editable": True, "deletable": True}


def index(*entries):
    return Answer(200, {"response": list(entries)})


def alpha(**attributes):
    return sg(42, SG, "Alpha", [ADMIN, ACME], [(0, None, False), (3, "Training", False)], **attributes)


def parsed(*entries):
    from application.models import sharingGroups
    return sharingGroups.parse(list(entries))


def org(id, uuid, name):
    return {"Organisation": {"id": str(id), "uuid": uuid, "name": name, "local": True}}


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
    from application.models import sharingGroups
    return sharingGroups


@pytest.fixture()
def fleet(db, make_user):
    """Three servers of one fleet, and one server of another fleet of the same user"""
    from application.DBModels import Fleet, Server
    user = make_user("sharing-groups@test.local")
    fleets = [Fleet(name=name, description="", user_id=user.id, timestamp=1) for name in ("sgs", "sgs other")]
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


@pytest.fixture()
def queued(monkeypatch):
    from application.workers import tasks
    calls = []
    monkeypatch.setattr(tasks, "runJob", lambda job_id: calls.append(job_id))
    return calls


def base(server):
    return f"/server-management/sharing-groups/{server.id}"


def urls(misp):
    return [url for _, url, _ in misp["posted"]]


# Records

def test_records_are_compacted_deduplicated_and_sorted(model):
    entry = sg(42, SG.upper(), "Zulu", [ACME, ADMIN, (1, UUID_ADMIN, "ADMIN", False)],
               [(3, "Training", False), (3, "Training", True), (0, None, False), (2, "Aaa", False)],
               local=True)
    entry["SharingGroupOrg"].append({"extend": True, "Organisation": {"name": "No UUID"}})
    groups = parsed(entry, sg(7, SG_BETA, "alpha"), {"SharingGroup": {"id": "9", "name": "No UUID"}},
                    sg(42, SG.upper(), "Zulu duplicate"))
    assert [g["name"] for g in groups] == ["alpha", "Zulu"]
    zulu = groups[1]
    assert zulu["id"] == 42 and zulu["uuid"] == SG and zulu["local"] is True and zulu["roaming"] is False
    assert [(m["name"], m["extend"]) for m in zulu["members"]] == [("Acme", False), ("ADMIN", True)]
    assert zulu["servers"] == [{"server_id": 0, "name": "Local instance", "all_orgs": False},
                               {"server_id": 2, "name": "Aaa", "all_orgs": False},
                               {"server_id": 3, "name": "Training", "all_orgs": True}]
    assert zulu["creator"]["uuid"] == UUID_ADMIN and zulu["editable"] and zulu["deletable"]


# Listing

def test_listing_reads_both_indexes_and_merges_them(fleet, misp, model):
    a = fleet["servers"][0]
    seen = []
    misp["answers"][("misp-a", INDEX)] = lambda: seen.append(INDEX) or index(sg(1, SG, "Alpha"))
    misp["answers"][("misp-a", PASSIVE)] = lambda: seen.append(PASSIVE) or index(
        sg(1, SG, "Alpha"), sg(2, SG_BETA, "Beta", active=False))
    result = model.sharingGroupsOf(a)
    assert seen == [INDEX, PASSIVE]
    assert [g["name"] for g in result["sharing_groups"]] == ["Alpha", "Beta"]


def test_listing_ignores_a_failing_passive_index(fleet, misp, model):
    a = fleet["servers"][0]
    misp["answers"][("misp-a", INDEX)] = index(sg(1, SG, "Alpha"))
    misp["answers"][("misp-a", PASSIVE)] = Answer(404, {"message": "Not found"})
    assert [g["name"] for g in model.sharingGroupsOf(a)["sharing_groups"]] == ["Alpha"]


def test_index_endpoint_caches_until_refreshed(client, auth_headers, fleet, misp, make_user):
    a = fleet["servers"][0]
    calls = []
    misp["answers"][("misp-a", INDEX)] = lambda: calls.append(1) or index(sg(1, SG, "Alpha"))
    headers = auth_headers(fleet["user"])
    first = client.get(base(a), headers=headers).get_json()
    assert first["server_id"] == a.id and first["cached"] is False and isinstance(first["fetched_at"], int)
    assert first["sharing_groups"][0]["name"] == "Alpha"
    assert client.get(base(a), headers=headers).get_json()["cached"] is True
    assert len(calls) == 1
    assert client.get(base(a) + "?refresh=1", headers=headers).get_json()["cached"] is False
    assert len(calls) == 2
    other = make_user("sharing-groups-other@test.local")
    assert client.get(base(a), headers=auth_headers(other)).status_code == 404


def test_index_endpoint_reports_misp_failures_and_caches_nothing(client, auth_headers, fleet, misp, model):
    a = fleet["servers"][0]
    response = client.get(base(a), headers=auth_headers(fleet["user"]))
    assert response.status_code == 502 and "Server unreachable" in response.get_json()["message"]
    assert model.readCached(a) is None


# Fleet comparison

def test_fleet_comparison_statuses(client, auth_headers, fleet, misp, model, monkeypatch):
    import application.models.utils as utils
    a, b, c, z = fleet["servers"]
    own = [alpha(), sg(2, SG_BETA, "Beta Group", [ADMIN])]
    misp["answers"][("misp-a", INDEX)] = index(*own)
    # b differs in everything compared, c only in what is not compared
    model.store(b, parsed(
        sg(5, SG, "Alpha Renamed", [ADMIN, CIRCL], [], active=False, roaming=True),
        sg(6, UUID_OTHER, "  beta   group", [ADMIN])), now=1000)
    model.store(c, parsed(sg(7, SG, "alpha", [(1, UUID_ADMIN, "ADMIN", False), ACME], [(9, "Other", True)])), now=2000)

    async def noFetch(*args, **kwargs):
        raise AssertionError("every list is cached")
    monkeypatch.setattr(utils, "asyncFetcher", noFetch)
    body = client.get(base(a) + "/fleet", headers=auth_headers(fleet["user"])).get_json()
    assert body["server_id"] == a.id and body["unavailable"] == []
    assert [s["id"] for s in body["compared"]] == [b.id, c.id]
    alphaResult = body["sharing_groups"][SG]
    assert alphaResult["same"] == [c.id] and alphaResult["other_uuid"] == []
    assert alphaResult["differs"] == [{"server_id": b.id, "name": "Alpha Renamed", "active": False, "roaming": True,
                                       "members_missing": [UUID_ACME], "members_extra": [[UUID_CIRCL, "CIRCL"]]}]
    assert body["sharing_groups"][SG_BETA] == {"same": [], "differs": [], "other_uuid": [[b.id, UUID_OTHER]]}


def test_fleet_comparison_fetches_the_other_servers(client, auth_headers, fleet, misp, model, monkeypatch):
    import application.models.utils as utils
    a, b, c, z = fleet["servers"]
    misp["answers"][("misp-a", INDEX)] = index(alpha())
    model.store(b, parsed(alpha()), now=1000)
    fetched = []

    async def fakeFetcher(server, urls, timeout=None):
        fetched.append((server.name, urls, timeout))
        return [UNREACHABLE]
    monkeypatch.setattr(utils, "asyncFetcher", fakeFetcher)
    body = client.get(base(a) + "/fleet", headers=auth_headers(fleet["user"])).get_json()
    # b from its cache, c unreadable (never "missing"), z in another fleet
    assert fetched == [("misp-c", [INDEX, PASSIVE], model.FLEET_TIMEOUT)]
    assert body["compared"] == [{"id": b.id, "name": "misp-b", "fetched_at": 1000}]
    assert body["unavailable"] == [{"id": c.id, "name": "misp-c", "error": "Server unreachable"}]
    assert body["sharing_groups"][SG] == {"same": [b.id], "differs": [], "other_uuid": []}


def test_fleet_comparison_caches_what_it_fetches(client, auth_headers, fleet, misp, model, monkeypatch):
    import application.models.utils as utils
    a, b, c, z = fleet["servers"]
    misp["answers"][("misp-a", INDEX)] = index(alpha())

    async def fakeFetcher(server, urls, timeout=None):
        return [{"response": [sg(8, SG_BETA, "Alpha")]}, UNREACHABLE]
    monkeypatch.setattr(utils, "asyncFetcher", fakeFetcher)
    body = client.get(base(a) + "/fleet?refresh=1", headers=auth_headers(fleet["user"])).get_json()
    assert body["unavailable"] == []
    assert body["sharing_groups"][SG]["other_uuid"] == [[b.id, SG_BETA], [c.id, SG_BETA]]
    assert model.readCached(c)["sharing_groups"][0]["uuid"] == SG_BETA


# Usage

def test_usage_counts_events_of_the_group(client, auth_headers, fleet, misp):
    a = fleet["servers"][0]
    misp["answers"][("misp-a", "POST /events/index")] = Counted(12)
    body = client.get(base(a) + "/usage/42", headers=auth_headers(fleet["user"])).get_json()
    assert body == {"group_id": 42, "events": 12}
    assert misp["posted"] == [("misp-a", "/events/index", {"sharinggroup": 42, "limit": 1})]


def test_usage_without_count_header(client, auth_headers, fleet, misp):
    a = fleet["servers"][0]
    misp["answers"][("misp-a", "POST /events/index")] = Counted(None)
    assert client.get(base(a) + "/usage/42", headers=auth_headers(fleet["user"])).get_json()["events"] is None


def test_usage_reports_misp_failures(client, auth_headers, fleet, misp):
    a = fleet["servers"][0]
    misp["answers"][("misp-a", "POST /events/index")] = Answer(500, {"message": "Broken"})
    assert client.get(base(a) + "/usage/42", headers=auth_headers(fleet["user"])).status_code == 502


# Add

def add(client, auth_headers, fleet, body):
    return client.post(base(fleet["servers"][0]) + "/add", headers=auth_headers(fleet["user"]), json=body)


@pytest.mark.parametrize("payload, field", [
    ({"description": "x"}, "name"),
    ({"name": "  "}, "name"),
    ({"name": "X", "uuid": "not-a-uuid"}, "uuid"),
    ({"name": "X", "members": [{"name": "A"}]}, "members"),
    ({"name": "X", "members": [{"uuid": UUID_ACME}]}, "members"),
    ({"name": "X", "members": [{"uuid": UUID_ACME, "name": "A", "extend": "yes"}]}, "members"),
    ({"name": "X", "servers": [{"server_id": True}]}, "servers"),
    ({"name": "X", "servers": [{"server_id": -1}]}, "servers"),
    ({"name": "X", "servers": [{"server_id": 1, "all_orgs": "yes"}]}, "servers"),
    ({"name": "X", "created": 1}, "created"),
])
def test_add_refuses_bad_input(client, auth_headers, fleet, misp, payload, field):
    response = add(client, auth_headers, fleet, payload)
    assert response.status_code == 400 and response.get_json()["field"] == field
    assert misp["posted"] == []


def test_add_refuses_a_taken_name(client, auth_headers, fleet, misp, model):
    model.store(fleet["servers"][0], parsed(alpha()))
    response = add(client, auth_headers, fleet, {"name": "  ALPHA "})
    assert response.status_code == 409 and response.get_json()["field"] == "name"
    assert misp["posted"] == []


def test_add_creates_the_group_flat(client, auth_headers, fleet, misp):
    from application.DBModels import Job
    a = fleet["servers"][0]
    misp["answers"][("misp-a", INDEX)] = lambda: index(alpha()) if misp["posted"] else index()
    response = add(client, auth_headers, fleet, {
        "name": " Alpha ", "uuid": SG.upper(), "members": [{"uuid": UUID_ADMIN, "name": "ADMIN", "extend": True},
                                                          {"uuid": UUID_ACME, "name": "Acme"}]})
    assert response.status_code == 200
    body = response.get_json()
    assert body["SharingGroup"]["uuid"] == SG and body["done"] == ["created"] and body["failed"] == []
    assert misp["posted"] == [("misp-a", "/sharing_groups/add", {
        "uuid": SG, "name": "Alpha", "description": "", "releasability": "", "active": True, "roaming": False,
        "SharingGroupOrg": [{"extend": True, "Organisation": {"uuid": UUID_ADMIN, "name": "ADMIN"}},
                            {"extend": False, "Organisation": {"uuid": UUID_ACME, "name": "Acme"}}]})]
    job = Job.query.filter_by(user_id=fleet["user"].id).one()
    assert job.kind == "server_management" and job.title == "Add sharing group Alpha on misp-a"
    assert len(job.results) == 1 and job.status == "done"


def test_add_generates_a_uuid(client, auth_headers, fleet, misp, model):
    misp["answers"][("misp-a", INDEX)] = index()
    assert add(client, auth_headers, fleet, {"name": "Alpha", "active": False, "roaming": True}).status_code == 200
    body = misp["posted"][0][2]
    assert model.UUID_RE.match(body["uuid"]) and body["active"] is False and body["roaming"] is True


def test_add_local_instance_open_to_all_reads_the_base_url(client, auth_headers, fleet, misp):
    misp["answers"][("misp-a", INDEX)] = index()
    misp["answers"][("misp-a", BASEURL)] = Answer(200, {"value": "https://misp.test"})
    add(client, auth_headers, fleet, {"name": "Alpha", "servers": [{"server_id": 0, "all_orgs": True}]})
    assert misp["posted"][0][2]["SharingGroupServer"] == [
        {"all_orgs": True, "Server": {"url": "https://misp.test", "all_orgs": True}}]


def test_add_local_instance_limited_to_members_sends_no_server(client, auth_headers, fleet, misp):
    misp["answers"][("misp-a", INDEX)] = index()  # The base URL is not readable: it must not be read
    response = add(client, auth_headers, fleet, {"name": "Alpha", "servers": [{"server_id": 0}]})
    assert response.status_code == 200
    assert "SharingGroupServer" not in misp["posted"][0][2] and len(misp["posted"]) == 1


def test_add_puts_remote_servers_afterwards(client, auth_headers, fleet, misp):
    misp["answers"][("misp-a", INDEX)] = lambda: index(alpha()) if misp["posted"] else index()
    body = add(client, auth_headers, fleet, {"name": "Alpha", "uuid": SG, "servers": [
        {"server_id": 3, "all_orgs": True}, {"server_id": 4}]}).get_json()
    assert urls(misp) == ["/sharing_groups/add", f"/sharing_groups/addServer/{SG}/3/1",
                          f"/sharing_groups/addServer/{SG}/4/0"]
    assert body["done"] == ["created", "server #3 added", "server #4 added"]


def test_add_roaming_ignores_servers(client, auth_headers, fleet, misp):
    misp["answers"][("misp-a", INDEX)] = index()
    add(client, auth_headers, fleet, {"name": "Alpha", "roaming": True, "servers": [{"server_id": 3}]})
    assert urls(misp) == ["/sharing_groups/add"]


def test_add_reports_misp_refusal(client, auth_headers, fleet, misp):
    misp["answers"][("misp-a", INDEX)] = index()
    misp["answers"][("misp-a", "POST /sharing_groups/add")] = Answer(403, {"message": "Not allowed to add"})
    response = add(client, auth_headers, fleet, {"name": "Alpha"})
    assert response.status_code == 502 and "Not allowed to add" in response.get_json()["message"]


# Edit

def edit(client, auth_headers, fleet, body, uuid=SG):
    return client.post(f"{base(fleet['servers'][0])}/edit/{uuid}", headers=auth_headers(fleet["user"]), json=body)


@pytest.fixture()
def current(misp):
    """Alpha is on misp-a: ADMIN (may extend) and Acme, the Local instance and Training"""
    misp["answers"][("misp-a", INDEX)] = index(alpha(description="old"), sg(2, SG_BETA, "Beta"))
    misp["answers"][("misp-a", BASEURL)] = Answer(200, {"value": "https://misp.test"})


def test_edit_sends_only_what_differs(client, auth_headers, fleet, misp, current):
    response = edit(client, auth_headers, fleet, {"name": "Alpha", "description": "new", "active": True,
                                                 "roaming": True})
    assert response.status_code == 200
    assert misp["posted"] == [("misp-a", f"/sharing_groups/edit/{SG}", {"description": "new", "roaming": True})]


def test_edit_sends_nothing_when_equal(client, auth_headers, fleet, misp, current):
    response = edit(client, auth_headers, fleet, {"name": "Alpha", "description": "old"})
    assert response.status_code == 200 and misp["posted"] == []


@pytest.mark.parametrize("payload", [{"uuid": SG, "name": "X"}, {}])
def test_edit_refuses_bad_input(client, auth_headers, fleet, misp, current, payload):
    assert edit(client, auth_headers, fleet, payload).status_code == 400
    assert misp["posted"] == []


def test_edit_refuses_a_taken_name(client, auth_headers, fleet, misp, current):
    response = edit(client, auth_headers, fleet, {"name": " beta"})
    assert response.status_code == 409 and response.get_json()["field"] == "name"
    assert misp["posted"] == []


def test_edit_members(client, auth_headers, fleet, misp, current):
    response = edit(client, auth_headers, fleet, {"members": [
        {"uuid": UUID_ADMIN, "name": "ADMIN", "extend": False}, {"uuid": UUID_CIRCL, "name": "CIRCL", "extend": True}]})
    assert response.status_code == 200
    assert urls(misp) == [f"/sharing_groups/removeOrg/{SG}/{UUID_ADMIN}", f"/sharing_groups/addOrg/{SG}/{UUID_ADMIN}/0",
                          f"/sharing_groups/addOrg/{SG}/{UUID_CIRCL}/1", f"/sharing_groups/removeOrg/{SG}/{UUID_ACME}"]


def test_edit_puts_the_old_extend_flag_back_when_it_cannot_change(client, auth_headers, fleet, misp, current):
    calls = []

    def addOrg(data):
        calls.append(1)
        return Answer(403, {"message": "Refused"}) if len(calls) == 1 else Answer(200, {"saved": True})
    misp["answers"][("misp-a", f"POST /sharing_groups/addOrg/{SG}/{UUID_ADMIN}/0")] = addOrg
    misp["answers"][("misp-a", f"POST /sharing_groups/addOrg/{SG}/{UUID_ADMIN}/1")] = addOrg
    response = edit(client, auth_headers, fleet, {"members": [
        {"uuid": UUID_ADMIN, "name": "ADMIN", "extend": False}, {"uuid": UUID_ACME, "name": "Acme"}]})
    assert response.status_code == 502 and "Failed:" in response.get_json()["message"]
    assert urls(misp) == [f"/sharing_groups/removeOrg/{SG}/{UUID_ADMIN}", f"/sharing_groups/addOrg/{SG}/{UUID_ADMIN}/0",
                          f"/sharing_groups/addOrg/{SG}/{UUID_ADMIN}/1"]


def test_edit_says_when_a_member_could_not_be_put_back(client, auth_headers, fleet, misp, current):
    for flag in (0, 1):
        misp["answers"][("misp-a", f"POST /sharing_groups/addOrg/{SG}/{UUID_ADMIN}/{flag}")] = \
            Answer(403, {"message": "Refused"})
    response = edit(client, auth_headers, fleet, {"members": [
        {"uuid": UUID_ADMIN, "name": "ADMIN", "extend": False}, {"uuid": UUID_ACME, "name": "Acme"}]})
    assert response.status_code == 502
    assert "taken out first and could not be put back" in response.get_json()["message"]


def test_edit_remote_servers(client, auth_headers, fleet, misp, current):
    misp["answers"][("misp-a", INDEX)] = index(sg(42, SG, "Alpha", [ADMIN], [(0, None, False), (3, "Training", False),
                                                                           (5, "Old", False)]))
    response = edit(client, auth_headers, fleet, {"servers": [
        {"server_id": 0}, {"server_id": 3, "all_orgs": True}, {"server_id": 7}]})
    assert response.status_code == 200
    assert urls(misp) == [f"/sharing_groups/removeServer/{SG}/3", f"/sharing_groups/addServer/{SG}/3/1",
                          f"/sharing_groups/addServer/{SG}/7/0", f"/sharing_groups/removeServer/{SG}/5"]


def test_edit_local_instance_goes_through_the_base_url(client, auth_headers, fleet, misp, current):
    response = edit(client, auth_headers, fleet, {"servers": [{"server_id": 0, "all_orgs": True},
                                                              {"server_id": 3}]})
    assert response.status_code == 200
    assert misp["posted"] == [("misp-a", f"/sharing_groups/edit/{SG}", {"SharingGroupServer": [
        {"all_orgs": True, "Server": {"url": "https://misp.test", "all_orgs": True}}]})]


def test_edit_cannot_remove_the_local_instance(client, auth_headers, fleet, misp, current):
    response = edit(client, auth_headers, fleet, {"servers": [{"server_id": 3}]})
    assert response.status_code == 502 and "Local instance not removed" in response.get_json()["message"]
    assert misp["posted"] == []


@pytest.mark.parametrize("entry, payload", [
    (alpha(roaming=True), {"servers": [{"server_id": 7}]}),
    (alpha(), {"roaming": True, "servers": [{"server_id": 7}]}),
])
def test_edit_leaves_servers_of_a_roaming_group_alone(client, auth_headers, fleet, misp, entry, payload):
    misp["answers"][("misp-a", INDEX)] = index(entry)
    assert edit(client, auth_headers, fleet, payload).status_code == 200
    assert all("Server" not in url for url in urls(misp))


def test_edit_group_gone_from_the_server(client, auth_headers, fleet, misp, current):
    response = edit(client, auth_headers, fleet, {"description": "x"}, uuid=UUID_OTHER)
    assert response.status_code == 502 and "not on the server any more" in response.get_json()["message"]


def test_edit_partial_failure_says_what_was_done_and_what_failed(client, auth_headers, fleet, misp, current):
    misp["answers"][("misp-a", f"POST /sharing_groups/addOrg/{SG}/{UUID_CIRCL}/0")] = Answer(
        403, {"message": "Unknown organisation"})
    message = edit(client, auth_headers, fleet, {"members": [
        {"uuid": UUID_ADMIN, "name": "ADMIN", "extend": True}, {"uuid": UUID_CIRCL, "name": "CIRCL"}]}).get_json()["message"]
    assert "Done: Acme removed" in message and "Failed: CIRCL added: " in message and "Unknown organisation" in message


# Delete

def delete(client, auth_headers, fleet, uuid=SG):
    return client.post(f"{base(fleet['servers'][0])}/delete/{uuid}", headers=auth_headers(fleet["user"]), json={})


def test_delete(client, auth_headers, fleet, misp, model):
    a = fleet["servers"][0]
    model.store(a, parsed(alpha()))
    response = delete(client, auth_headers, fleet)
    assert response.status_code == 200 and response.get_json() == {"deleted": SG}
    assert misp["posted"] == [("misp-a", f"/sharing_groups/delete/{SG}", {})]
    assert model.readCached(a) is None


@pytest.mark.parametrize("status, words", [
    (403, ("events", "attributes", "objects", "reports")),
    (405, ("API user", "gone")),
])
def test_delete_refusals_are_explained(client, auth_headers, fleet, misp, model, status, words):
    a = fleet["servers"][0]
    model.store(a, parsed(alpha()))
    misp["answers"][("misp-a", f"POST /sharing_groups/delete/{SG}")] = Answer(status, {"message": "No"})
    response = delete(client, auth_headers, fleet)
    assert response.status_code == 502
    assert all(word in response.get_json()["message"] for word in words)
    assert model.readCached(a) is None


# Copy to other servers

def test_copy_starts_a_job(client, auth_headers, fleet, misp, model, queued):
    from application.DBModels import Job
    a, b, c, _ = fleet["servers"]
    misp["answers"][("misp-a", INDEX)] = index(alpha())
    headers = auth_headers(fleet["user"])
    response = client.post(base(a) + "/copy", headers=headers, json={"uuid": SG.upper(), "server_ids": [b.id]})
    assert response.status_code == 202
    body = response.get_json()
    assert queued == [body["job_id"]]
    job = Job.query.get(body["job_id"])
    assert job.kind == "sharing_group_copy" and job.title == "Sharing group Alpha on misp-b"
    assert job.secret_params == model.copyParams(parsed(alpha())[0])
    response = client.post(base(a) + "/copy", headers=headers, json={"uuid": SG, "server_ids": [c.id, b.id, c.id]})
    job = Job.query.get(response.get_json()["job_id"])
    assert job.title == "Sharing group Alpha on 2 servers" and [r.server_id for r in job.results] == [b.id, c.id]


@pytest.mark.parametrize("body, status, field", [
    ({"uuid": SG, "server_ids": []}, 400, "server_ids"),
    ({"uuid": SG, "server_ids": ["two"]}, 400, "server_ids"),
    ({"uuid": "nope", "server_ids": ["B"]}, 400, "uuid"),
    ({"uuid": SG, "server_ids": ["A"]}, 400, "server_ids"),
    ({"uuid": SG, "server_ids": ["Z"]}, 400, "server_ids"),
    ({"uuid": SG, "server_ids": [999999]}, 404, None),
    ({"uuid": UUID_OTHER, "server_ids": ["B"]}, 404, "uuid"),
])
def test_copy_refuses_bad_input(client, auth_headers, fleet, misp, queued, body, status, field):
    a, b, _, z = fleet["servers"]
    named = {"A": a.id, "B": b.id, "Z": z.id}
    body = dict(body, server_ids=[named.get(id, id) if isinstance(id, str) else id for id in body["server_ids"]])
    misp["answers"][("misp-a", INDEX)] = index(alpha())
    response = client.post(base(a) + "/copy", headers=auth_headers(fleet["user"]), json=body)
    assert response.status_code == status
    if field:
        assert response.get_json()["field"] == field
    assert queued == []


# Copy unit

@pytest.fixture()
def source(model):
    group = parsed(sg(42, SG, "Alpha", [ADMIN, ACME, CIRCL], [(0, None, False), (3, "Training", False),
                                                              (4, "Other", True)]))[0]
    return model.copyParams(group)


def test_copy_unit_creates_the_group(fleet, misp, model, source):
    b = fleet["servers"][1]
    misp["answers"][("misp-b", INDEX)] = index()
    unit = model.copyUnit(b, source)
    assert unit.ok and unit.response["created"] is True
    assert unit.summary == "Created (its 2 servers not copied: add them there if needed)"
    assert misp["posted"] == [("misp-b", "/sharing_groups/add", {
        "uuid": SG, "name": "Alpha", "description": "", "releasability": "", "active": True, "roaming": False,
        "SharingGroupOrg": [{"extend": False, "Organisation": {"uuid": UUID_ACME, "name": "Acme"}},
                            {"extend": True, "Organisation": {"uuid": UUID_ADMIN, "name": "ADMIN"}},
                            {"extend": False, "Organisation": {"uuid": UUID_CIRCL, "name": "CIRCL"}}]})]


def test_copy_unit_says_nothing_of_servers_when_there_are_none(fleet, misp, model):
    b = fleet["servers"][1]
    misp["answers"][("misp-b", INDEX)] = index()
    assert model.copyUnit(b, model.copyParams(parsed(sg(1, SG, "Alpha"))[0])).summary == "Created"


@pytest.mark.parametrize("theirs, summary", [
    (sg(5, SG, "alpha", [ADMIN, ACME, CIRCL]), "Already complete"),
    (sg(5, SG, "Alpha", [ADMIN, ACME, CIRCL, (9, UUID_OTHER, "More", False)]), "Already complete"),
    (sg(5, SG, "Alpha 2", [ADMIN, ACME, CIRCL], active=False, roaming=True),
     "Already complete (named `Alpha 2` there, inactive there, roaming there, left as it is)"),
])
def test_copy_unit_already_complete(fleet, misp, model, source, theirs, summary):
    b = fleet["servers"][1]
    misp["answers"][("misp-b", INDEX)] = index(theirs)
    unit = model.copyUnit(b, source)
    assert unit.ok and unit.summary == summary and misp["posted"] == []


def test_copy_unit_adds_missing_members_creating_unknown_organisations(fleet, misp, model, source):
    b = fleet["servers"][1]
    misp["answers"][("misp-b", INDEX)] = index(sg(5, SG, "Alpha", [ADMIN]))
    misp["answers"][("misp-b", ORG_INDEX)] = Answer(200, [org(1, UUID_ADMIN, "ADMIN"), org(2, UUID_ACME, "Acme")])
    unit = model.copyUnit(b, source)
    assert unit.ok and unit.summary == "Added 2 members (1 organisation created)"
    assert misp["posted"] == [
        ("misp-b", f"/sharing_groups/addOrg/{SG}/{UUID_ACME}/0", {}),
        ("misp-b", "/admin/organisations/add", {"Organisation": {"uuid": UUID_CIRCL, "name": "CIRCL", "local": False}}),
        ("misp-b", f"/sharing_groups/addOrg/{SG}/{UUID_CIRCL}/0", {})]


def test_copy_unit_reports_how_far_it_got_when_adding_fails(fleet, misp, model, source):
    b = fleet["servers"][1]
    misp["answers"][("misp-b", INDEX)] = index(sg(5, SG, "Alpha", [ADMIN]))
    misp["answers"][("misp-b", ORG_INDEX)] = Answer(200, [org(2, UUID_ACME, "Acme"), org(3, UUID_CIRCL, "CIRCL")])
    misp["answers"][("misp-b", f"POST /sharing_groups/addOrg/{SG}/{UUID_CIRCL}/0")] = Answer(403, {"message": "No"})
    unit = model.copyUnit(b, source)
    assert not unit.ok and unit.http_status == 403
    assert unit.summary.startswith("Could not add CIRCL (1 of 2 added before)")


def test_copy_unit_never_duplicates_a_name(fleet, misp, model, source):
    b = fleet["servers"][1]
    misp["answers"][("misp-b", INDEX)] = index(sg(5, UUID_OTHER, "ALPHA"))
    unit = model.copyUnit(b, source)
    assert not unit.ok and UUID_OTHER in unit.summary and misp["posted"] == []


def test_copy_unit_reports_listing_failures(fleet, misp, model, source):
    unit = model.copyUnit(fleet["servers"][1], source)
    assert not unit.ok and "Server unreachable" in unit.summary and misp["posted"] == []


def test_copy_runs_as_a_job(app, fleet, misp, model, source):
    """The unit wired into the job runner, end to end on two servers"""
    import application.models.jobRunner as jobRunner
    import application.models.jobs as jobModel
    _, b, c, _ = fleet["servers"]
    misp["answers"][("misp-b", INDEX)] = index()
    misp["answers"][("misp-c", INDEX)] = index(sg(5, SG, "Alpha", [ADMIN, ACME, CIRCL]))
    job = jobModel.create(fleet["user"], "sharing_group_copy", [b, c], params=source, title="copy")
    job = jobRunner.run(job.id, max_concurrency=1)
    assert job.status == "done" and job.succeeded == 2
    assert sorted(result.summary.split(" (")[0] for result in job.results) == ["Already complete", "Created"]
