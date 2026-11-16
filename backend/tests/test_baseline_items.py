"""Organisations, sharing groups and custom galaxies in baselines: rules describe the item as a reference server lists
it, drift says what differs, and a fix creates or completes the item (a custom galaxy is copied from the server the
rule names)"""
import copy

import pytest

from test_baselines import add, api, owner  # noqa: F401
from test_drift import (CONTENT_ANSWERS, ORG_ALB, ORG_BGR, SG_NATO, addRules, checks, evaluate, fleet,  # noqa: F401
                        okStatus, rule, setStatus, snapshotWith)
from test_remediation import published  # noqa: F401

CUSTOM = "cd6e3ac8-a8c4-4df7-9bfb-c4fe538ae439"
GONE = "0f0f0f0f-0000-4000-8000-000000000000"
CLUSTER_1 = "39940e29-d044-4431-8b45-8a7493042413"
CLUSTER_2 = "49940e29-d044-4431-8b45-8a7493042414"
ORG_EST = "5d1b0c8e-0d0a-4a8b-9f43-0000000000e5"

GALAXIES = [
    {"Galaxy": {"id": "155", "uuid": "5165f976-6b17-4131-bcfc-652d1b11cc01", "name": "FireHOL IPsets",
                "namespace": "firehol-ipsets", "type": "IPset", "enabled": True, "default": True}},
    {"Galaxy": {"id": "118", "uuid": CUSTOM.upper(), "name": "Named Threats", "namespace": "ls26", "type": CUSTOM,
                "enabled": False, "default": False}},
]
CLUSTERS = [{"GalaxyCluster": {"uuid": CLUSTER_1, "version": "100", "deleted": False}},
            {"GalaxyCluster": {"uuid": CLUSTER_2, "version": "7", "deleted": True}}]


def answers(**overrides):
    data = copy.deepcopy({**CONTENT_ANSWERS, "/galaxies/index": GALAXIES,
                          f"/galaxy_clusters/index/{CUSTOM}": CLUSTERS,
                          f"/galaxy_clusters/index/{GONE}": {"_status_code": 404, "message": "Invalid Galaxy."}})
    data.update(overrides)
    return data


def itemState(galaxies=(CUSTOM,), **overrides):
    from application.models.baselineDrift import ContentPlan
    plan = ContentPlan(["organisation", "sharing_group", "custom_galaxy"], galaxies)
    given = answers(**overrides)
    return plan.state([given[url] for url in plan.urls], now=1)


# Rules

def test_item_rules_are_validated(owner, api):  # noqa: F811
    user, (alpha, beta) = owner
    source = alpha.servers[0]
    response = add(api(user), alpha,
                   {"type": "organisation", "key": ORG_ALB.upper(), "label": "ignored",
                    "expected": {"name": " team-ALB ", "type": "", "nationality": "Albania", "local": "1"}},
                   {"type": "sharing_group", "key": SG_NATO,
                    "expected": {"name": "NATO Nations", "releasability": "NATO",
                                 "members": [{"uuid": ORG_BGR, "name": "team-BGR"},
                                             {"uuid": ORG_ALB.upper(), "name": "team-ALB", "extend": True},
                                             {"uuid": ORG_BGR, "name": "team-BGR"}]}},
                   {"type": "custom_galaxy", "key": CUSTOM,
                    "expected": {"name": "Named Threats", "namespace": "ls26", "source_server_id": source.id,
                                 "clusters": {CLUSTER_1.upper(): "100"}}})
    assert response.status_code == 201, response.get_json()
    org, sg, galaxy = response.get_json()["rules"]
    assert (org["key"], org["label"]) == (ORG_ALB, "team-ALB")
    assert org["expected"] == {"name": "team-ALB", "nationality": "Albania", "local": True}
    assert org["remediable"] is True and org["comparator"] == "eq"
    assert sg["expected"] == {"name": "NATO Nations", "releasability": "NATO", "description": "", "roaming": False,
                              "members": [{"uuid": ORG_ALB, "name": "team-ALB", "extend": True},
                                          {"uuid": ORG_BGR, "name": "team-BGR", "extend": False}]}
    assert galaxy["label"] == "ls26 :: Named Threats"
    assert galaxy["expected"] == {"name": "Named Threats", "namespace": "ls26", "source_server_id": source.id,
                                  "clusters": {CLUSTER_1: 100}}


@pytest.mark.parametrize("rule, field", [
    ({"type": "organisation", "key": "not-a-uuid", "expected": {"name": "x"}}, "key"),
    ({"type": "organisation", "key": ORG_ALB, "expected": {"name": " "}}, "expected"),
    ({"type": "organisation", "key": ORG_ALB, "expected": "team-ALB"}, "expected"),
    ({"type": "sharing_group", "key": SG_NATO, "expected": {"name": "x", "members": [{"uuid": "x", "name": "y"}]}},
     "expected"),
    ({"type": "sharing_group", "key": SG_NATO, "expected": {"name": "x", "members": [{"uuid": ORG_ALB}]}},
     "expected"),
    ({"type": "custom_galaxy", "key": CUSTOM, "expected": {"name": "x", "clusters": {}}}, "expected"),
    ({"type": "custom_galaxy", "key": CUSTOM, "expected": {"name": "x", "source_server_id": 1,
                                                           "clusters": {CLUSTER_1: "new"}}}, "expected"),
])
def test_invalid_item_rules_are_refused(owner, api, rule, field):  # noqa: F811
    user, (alpha, beta) = owner
    response = add(api(user), alpha, rule)
    assert response.status_code == 400
    assert response.get_json()["errors"][0]["field"] == field


def test_a_galaxy_is_only_copied_from_the_owners_servers(db, owner, api, make_user):  # noqa: F811
    user, (alpha, beta) = owner
    theirs = strangerServer(db, make_user, "stranger-galaxy@test.test")
    response = add(api(user), alpha, {"type": "custom_galaxy", "key": CUSTOM, "expected": {
        "name": "x", "source_server_id": theirs.id, "clusters": {}}})
    assert response.get_json()["errors"][0]["message"] == "Unknown source server"
    dropServer(db, theirs)


def strangerServer(db, make_user, email):
    """A server of another user"""
    from application.DBModels import Fleet, Server
    stranger = make_user(email)
    theirFleet = Fleet(name="Theirs", description="", user_id=stranger.id, timestamp=1)
    db.session.add(theirFleet)
    db.session.commit()
    theirs = Server(name="theirs", url="https://theirs.test", user_id=stranger.id, fleet_id=theirFleet.id)
    db.session.add(theirs)
    db.session.commit()
    return theirs


def dropServer(db, server):
    fleet = server.fleet
    db.session.delete(server)
    db.session.delete(fleet)
    db.session.commit()


# Content and drift

def test_content_plan_lists_the_clusters_of_custom_galaxies():
    from application.models.baselineDrift import ContentPlan
    plan = ContentPlan(["custom_galaxy", "galaxy_enabled", "organisation"], [GONE, CUSTOM, CUSTOM])
    assert plan.urls == ["/galaxies/index", "/organisations/index/scope:all",
                         f"/galaxy_clusters/index/{GONE}", f"/galaxy_clusters/index/{CUSTOM}"]
    assert ContentPlan(["organisation"], [CUSTOM]).galaxies == []

    state = itemState(galaxies=(CUSTOM, GONE))
    assert state["customGalaxies"]["items"] == {
        CUSTOM: {"name": "Named Threats", "namespace": "ls26", "enabled": False, "clusters": {CLUSTER_1: 100}}}
    assert state["organisations"]["items"][ORG_ALB] == {"name": "team-ALB", "type": "MIL", "nationality": "Albania",
                                                        "sector": "", "local": True}
    assert state["sharingGroups"]["items"][SG_NATO]["members"] == {ORG_ALB: {"name": "team-ALB", "extend": True}}

    failed = itemState(**{f"/galaxy_clusters/index/{CUSTOM}": {"error": "Timeout Exception (60s)"},
                          "/sharing_groups/index": {"_status_code": 403, "error": "Authentication error"}})
    assert failed["customGalaxies"]["items"][CUSTOM]["clusters_error"] == \
        "Could not list the galaxy clusters: Timeout Exception (60s)"
    assert failed["sharingGroups"] == {"error": "Could not list the sharing groups: Authentication error"}


def test_item_rules_are_judged():
    sgExpected = {"name": "NATO Nations", "releasability": "NATO", "description": "",
                  "members": [{"uuid": ORG_ALB, "name": "team-ALB"}, {"uuid": ORG_BGR, "name": "team-BGR"}]}
    rules = [
        rule(1, "organisation", ORG_ALB, {"name": "team-ALB", "nationality": "Albania"}),
        rule(2, "organisation", ORG_ALB, {"name": "team-ALB", "type": "CERT", "local": False}),
        rule(3, "organisation", ORG_EST, {"name": "team-EST"}),
        rule(4, "sharing_group", SG_NATO, {"name": "NATO Nations", "members": [{"uuid": ORG_ALB, "name": "team-ALB"}]}),
        rule(5, "sharing_group", SG_NATO, sgExpected),
        rule(6, "custom_galaxy", CUSTOM, {"name": "Named Threats", "clusters": {CLUSTER_1: 100}}),
        rule(7, "custom_galaxy", CUSTOM, {"name": "Named Threats", "clusters": {CLUSTER_1: 101, CLUSTER_2: 1}}),
        rule(8, "custom_galaxy", GONE, {"name": "Gone", "clusters": {}}),
    ]
    results = evaluate(rules, snapshotWith(content=itemState()))
    assert results[1].state == "match"
    assert results[2].state == "drift"
    assert results[2].reason == "Type `MIL` instead of `CERT`; local instead of external"
    assert (results[3].state, results[3].actual, results[3].reason) == ("drift", None, "Not on this server")
    assert results[4].state == "match"
    assert (results[5].state, results[5].reason) == ("drift", "1 member missing: team-BGR")
    assert results[5].actual["members"] == 1 and results[5].actual["missing"] == 1
    # Disabled on the server: drift even with every cluster
    assert (results[6].state, results[6].reason) == ("drift", "Disabled")
    assert results[7].reason == "Disabled; 1 cluster missing; 1 cluster older than on the reference"
    assert results[7].actual == {"enabled": False, "clusters": 1, "missing": 1, "older": 1}
    assert results[8].state == "drift" and results[8].actual is None

    unlisted = evaluate(rules, snapshotWith(content=itemState(galaxies=())))
    assert (unlisted[6].state, unlisted[6].reason) == ("unknown", "Its clusters were not listed yet")
    assert evaluate(rules, snapshotWith(content={"timestamp": 1}))[1].reason == "Its organisations were not listed yet"


def test_item_drift_is_a_health_issue_without_the_whole_rule(fleet, client, auth_headers):  # noqa: F811
    from application import redisModel
    user, theFleet, (beta, alpha) = fleet
    headers = auth_headers(user)
    for server in (beta, alpha):
        setStatus(server, okStatus())
        redisModel.saveServerInfo(server.uuid, snapshotWith(content=itemState()))
    sg, galaxy = addRules(client, headers, theFleet,
                          {"type": "sharing_group", "key": SG_NATO, "expected": {
                              "name": "NATO Nations", "members": [{"uuid": ORG_BGR, "name": "team-BGR"}]}},
                          {"type": "custom_galaxy", "key": CUSTOM, "expected": {
                              "name": "Named Threats", "namespace": "ls26", "source_server_id": alpha.id,
                              "clusters": {CLUSTER_1: 100}}})
    response = client.get(f"/health/issues?server_id={beta.id}&include_acked=1", headers=headers)
    found = {issue["evidence"]["rule_id"]: issue for issue in response.get_json() if issue["rule"] == "baseline_drift"}
    assert found[sg["id"]]["title"] == "Sharing group NATO Nations differs from the baseline"
    assert found[sg["id"]]["detail"] == "1 member missing: team-BGR."
    assert found[galaxy["id"]]["evidence"]["expected"] == {"name": "ls26 :: Named Threats"}


def test_a_new_galaxy_rule_checks_servers_that_never_listed_its_clusters(fleet, client, auth_headers, checks):  # noqa: F811,E501
    from application import redisModel
    user, theFleet, (beta, alpha) = fleet
    headers = auth_headers(user)
    redisModel.saveServerInfo(beta.uuid, snapshotWith(content=itemState()))
    redisModel.saveServerInfo(alpha.uuid, snapshotWith(content=itemState(galaxies=())))
    checks.clear()
    addRules(client, headers, theFleet, {"type": "custom_galaxy", "key": CUSTOM, "expected": {
        "name": "Named Threats", "source_server_id": beta.id, "clusters": {CLUSTER_1: 100}}})
    assert checks == [[alpha.id]]


# Fixes

class FakeMisp:
    """The organisations, sharing groups and custom galaxies of each server, through the mispOps calls a fix makes"""

    def __init__(self):
        self.orgs = {}
        self.sgs = {}
        self.galaxies = {}
        self.writes = []

    def seed(self, server, orgs=(), sgs=(), galaxies=()):
        from application.models import mispOps
        self.orgs[server.id] = mispOps.parseOrganisations([o["Organisation"] for o in orgs])
        self.sgs[server.id] = mispOps.parseSharingGroups(list(sgs))
        self.galaxies[server.id] = {uuid: dict(galaxy) for uuid, galaxy in galaxies}

    def organisations(self, server):
        return copy.deepcopy(self.orgs[server.id])

    def addOrganisation(self, server, uuid, fields, local):
        self.writes.append(("add org", server.id, uuid, fields, local))
        self.orgs[server.id][uuid] = {"id": 50 + len(self.orgs[server.id]), "name": "", "type": "",
                                      "nationality": "", "sector": "", **fields, "local": local}

    def editOrganisation(self, server, orgId, changes):
        self.writes.append(("edit org", server.id, orgId, changes))
        for org in self.orgs[server.id].values():
            if org["id"] == orgId:
                org.update(changes)

    def sharingGroups(self, server):
        return copy.deepcopy(self.sgs[server.id])

    def captureSharingGroup(self, server, payload):
        self.writes.append(("capture sg", server.id, copy.deepcopy(payload)))
        sg = self.sgs[server.id].setdefault(payload["uuid"], {"id": 9, "name": "", "releasability": "",
                                                              "description": "", "active": True, "roaming": False,
                                                              "members": {}})
        sg.update({field: payload[field] for field in ("name", "releasability", "description", "active", "roaming")
                   if field in payload})
        for member in payload["SharingGroupOrg"]:
            sg["members"][member["Organisation"]["uuid"]] = {"name": member["Organisation"]["name"],
                                                             "extend": member["extend"]}

    def listing(self, server, url, model, what):
        assert url == "/galaxies/index"
        return [{"id": str(galaxy["id"]), "uuid": uuid, "name": galaxy["name"], "namespace": "ls26",
                 "enabled": galaxy["enabled"], "default": False} for uuid, galaxy in self.galaxies[server.id].items()]

    def galaxyClusters(self, server, uuid):
        galaxy = self.galaxies[server.id].get(uuid)
        return dict(galaxy["clusters"]) if galaxy else None

    def exportGalaxyClusters(self, server, galaxyId):
        galaxy = next(g for g in self.galaxies[server.id].values() if g["id"] == galaxyId)
        return [{"GalaxyCluster": {"uuid": uuid, "version": str(version), "Galaxy": {"name": galaxy["name"]}}}
                for uuid, version in galaxy["clusters"].items()]

    def importGalaxyClusters(self, server, clusters):
        self.writes.append(("import", server.id, len(clusters)))
        galaxy = self.galaxies[server.id].setdefault(CUSTOM, {"id": 300, "name": "Named Threats", "enabled": True,
                                                              "clusters": {}})
        for cluster in clusters:
            galaxy["clusters"][cluster["GalaxyCluster"]["uuid"]] = int(cluster["GalaxyCluster"]["version"])

    def setGalaxyEnabled(self, server, galaxyId, enabled):
        self.writes.append(("enable galaxy", server.id, galaxyId, enabled))
        for galaxy in self.galaxies[server.id].values():
            if galaxy["id"] == galaxyId:
                galaxy["enabled"] = enabled


@pytest.fixture()
def misp(monkeypatch):
    from application.models import mispOps
    fake = FakeMisp()
    for name in ("organisations", "addOrganisation", "editOrganisation", "sharingGroups", "captureSharingGroup",
                 "listing", "galaxyClusters", "exportGalaxyClusters", "importGalaxyClusters", "setGalaxyEnabled"):
        monkeypatch.setattr(mispOps, name, getattr(fake, name))
    return fake


def driftingItems(client, headers, theFleet, beta, alpha, misp):
    """beta lacks team-EST, has team-ALB under another name, lacks a member of NATO Nations and the custom galaxy;
    alpha has everything and is the galaxy's source"""
    from application import redisModel
    orgs = copy.deepcopy(CONTENT_ANSWERS["/organisations/index/scope:all"])
    orgs[0]["Organisation"]["name"] = "team-ALB_4174"
    misp.seed(beta, orgs=orgs, sgs=copy.deepcopy(CONTENT_ANSWERS["/sharing_groups/index"]["response"]))
    misp.seed(alpha, galaxies=[(CUSTOM, {"id": 118, "name": "Named Threats", "enabled": True,
                                         "clusters": {CLUSTER_1: 100}})])
    redisModel.saveServerInfo(beta.uuid, snapshotWith(content=itemState(**{
        "/organisations/index/scope:all": orgs,
        "/galaxies/index": GALAXIES[:1]})))
    for server in (beta, alpha):
        setStatus(server, okStatus())
    return addRules(client, headers, theFleet,
                    {"type": "sharing_group", "key": SG_NATO, "expected": {
                        "name": "NATO Nations", "releasability": "NATO",
                        "members": [{"uuid": ORG_ALB, "name": "team-ALB", "extend": True},
                                    {"uuid": ORG_EST, "name": "team-EST"}]}},
                    {"type": "organisation", "key": ORG_ALB, "expected": {"name": "team-ALB"}},
                    {"type": "organisation", "key": ORG_EST, "expected": {"name": "team-EST", "sector": "Defence"}},
                    {"type": "custom_galaxy", "key": CUSTOM, "expected": {
                        "name": "Named Threats", "namespace": "ls26", "source_server_id": alpha.id,
                        "clusters": {CLUSTER_1: 100}}})


def test_preview_and_job_keep_item_rules_short(fleet, client, auth_headers, misp, published, monkeypatch):  # noqa: F811,E501
    from application.workers import tasks
    monkeypatch.setattr(tasks, "runJob", lambda job_id: None)
    user, theFleet, (beta, alpha) = fleet
    headers = auth_headers(user)
    sg, alb, est, galaxy = driftingItems(client, headers, theFleet, beta, alpha, misp)
    body = client.post(f"/baselines/fleet/{theFleet.id}/remediation/preview", json={"server_ids": [beta.id]},
                       headers=headers).get_json()
    items = {item["rule_id"]: item for item in body["servers"][0]["items"]}
    assert set(items) == {sg["id"], alb["id"], est["id"], galaxy["id"]}
    assert all(item["action"] == "apply" for item in items.values())
    assert items[sg["id"]]["expected"] == {"name": "NATO Nations", "members": 2}
    assert items[sg["id"]]["difference"] == "1 member missing: team-EST"
    assert items[galaxy["id"]]["expected"] == {"name": "Named Threats", "clusters": 1}
    assert items[alb["id"]]["difference"] == "Name `team-ALB_4174` instead of `team-ALB`"

    response = client.post(f"/baselines/fleet/{theFleet.id}/remediation",
                           json={"items": [{"server_id": beta.id, "rule_id": sg["id"]}]}, headers=headers)
    from application.DBModels import BaselineRule, Job, db
    params = db.session.get(Job, response.get_json()["job_id"]).secret_params
    assert params["servers"][str(beta.id)][0]["expected"] == {"name": "NATO Nations", "members": 2}

    # The source of a galaxy gone: by hand
    db.session.get(BaselineRule, galaxy["id"]).expected = {**galaxy["expected"], "source_server_id": 999999}
    db.session.commit()
    body = client.post(f"/baselines/fleet/{theFleet.id}/remediation/preview", json={"rule_ids": [galaxy["id"]]},
                       headers=headers).get_json()
    item = body["servers"][0]["items"][0]
    assert item["action"] == "manual" and item["reason"].startswith("The server this galaxy is copied from")


def test_the_unit_creates_and_completes_items(fleet, client, auth_headers, misp, published):  # noqa: F811
    from application.models.baselineRemediation import remediationUnit
    user, theFleet, (beta, alpha) = fleet
    headers = auth_headers(user)
    sg, alb, est, galaxy = driftingItems(client, headers, theFleet, beta, alpha, misp)
    short = lambda rule: {"rule_id": rule["id"], "type": rule["type"], "key": rule["key"],  # noqa: E731
                          "label": rule["label"], "comparator": "eq", "expected": {"name": "short"}}
    plan = [short(sg), short(alb), short(est), short(galaxy),
            {**short(est), "rule_id": 123456}]
    unit = remediationUnit(beta, {"fleet_id": theFleet.id, "servers": {str(beta.id): plan}})

    outcomes = {o["rule_id"]: o for o in unit.response["rules"]}
    # Organisations go first, then sharing groups
    assert [w[0] for w in misp.writes] == ["edit org", "add org", "capture sg", "import"]
    assert misp.writes[0] == ("edit org", beta.id, 1, {"name": "team-ALB"})
    assert misp.writes[1] == ("add org", beta.id, ORG_EST, {"name": "team-EST", "sector": "Defence"}, False)
    # Only the missing member is sent: the others stay as they are
    payload = misp.writes[2][2]
    assert payload == {"uuid": SG_NATO, "name": "NATO Nations", "releasability": "NATO",
                       "SharingGroupOrg": [{"extend": False, "Organisation": {"uuid": ORG_EST, "name": "team-EST"}}]}
    assert misp.galaxies[beta.id][CUSTOM]["clusters"] == {CLUSTER_1: 100}
    for rule in (sg, alb, est, galaxy):
        assert outcomes[rule["id"]]["status"] == "fixed", outcomes[rule["id"]]
    assert outcomes[alb["id"]]["before"]["name"] == "team-ALB_4174"
    assert outcomes[sg["id"]]["expected"] == {"name": "short"}
    assert outcomes[123456] == {**outcomes[123456], "status": "error",
                                "message": "The rule was removed from the baseline"}
    assert unit.summary == "4 fixed, 1 failed (team-EST: The rule was removed from the baseline)"

    # Drift follows at once
    body = client.get(f"/baselines/fleet/{theFleet.id}/drift", headers=headers).get_json()
    row = next(server for server in body["servers"] if server["id"] == beta.id)
    assert {row["results"][str(rule["id"])]["state"] for rule in (sg, alb, est, galaxy)} == {"match"}

    # Run again: nothing left to change
    misp.writes.clear()
    unit = remediationUnit(beta, {"fleet_id": theFleet.id, "servers": {str(beta.id): plan[:4]}})
    assert misp.writes == [] and unit.summary == "4 already as expected"


def test_a_missing_sharing_group_is_created_whole(fleet, client, auth_headers, misp, published):  # noqa: F811
    from application.models.baselineRemediation import remediationUnit
    user, theFleet, (beta, alpha) = fleet
    headers = auth_headers(user)
    sg, *_ = driftingItems(client, headers, theFleet, beta, alpha, misp)
    misp.sgs[beta.id] = {}
    item = {"rule_id": sg["id"], "type": "sharing_group", "key": SG_NATO, "label": "", "expected": {}}
    unit = remediationUnit(beta, {"fleet_id": theFleet.id, "servers": {str(beta.id): [item]}})
    assert unit.ok, unit.response
    payload = misp.writes[-1][2]
    assert payload["active"] is True and payload["roaming"] is False and payload["description"] == ""
    assert [member["Organisation"]["uuid"] for member in payload["SharingGroupOrg"]] == [ORG_ALB, ORG_EST]


def test_a_galaxy_is_not_copied_from_another_users_server(fleet, client, auth_headers, misp, published, db,  # noqa: F811
                                                          make_user):
    from application.DBModels import BaselineRule
    from application.models.baselineRemediation import remediationUnit
    user, theFleet, (beta, alpha) = fleet
    headers = auth_headers(user)
    *_, galaxy = driftingItems(client, headers, theFleet, beta, alpha, misp)
    theirs = strangerServer(db, make_user, "stranger-galaxy-unit@test.test")
    rule = db.session.get(BaselineRule, galaxy["id"])
    rule.expected = {**rule.expected, "source_server_id": theirs.id}
    db.session.commit()
    item = {"rule_id": galaxy["id"], "type": "custom_galaxy", "key": CUSTOM, "label": "", "expected": {}}
    unit = remediationUnit(beta, {"fleet_id": theFleet.id, "servers": {str(beta.id): [item]}})
    assert unit.response["rules"][0]["message"] == "The server this galaxy is copied from no longer exists"
    assert misp.writes == []
    dropServer(db, theirs)
