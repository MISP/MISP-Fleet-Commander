"""Organisations that do not line up across a fleet: the digests every listing leaves, the fleet's findings and
their cache, the health rule, and the full refresh listing organisations when there is another server to compare"""
import asyncio
import copy
import random

import pytest

from test_organisations import INDEX, listing, org
from test_plugin_failures import Answer

U1 = "11111111-0000-4000-8000-000000000001"
U2 = "11111111-0000-4000-8000-000000000002"
U3 = "11111111-0000-4000-8000-000000000003"
U4 = "11111111-0000-4000-8000-000000000004"


@pytest.fixture(autouse=True)
def _app(app):
    return app


@pytest.fixture()
def digests():
    from application.models import organisationDigests
    return organisationDigests


@pytest.fixture()
def fleet(db, make_user):
    """Three servers of one fleet, one alone in another fleet"""
    from application import redisClient
    from application.DBModels import Fleet, Server
    user = make_user("org-mismatch@test.local")
    fleets = [Fleet(name=name, description="", user_id=user.id, timestamp=1) for name in ("mm", "mm alone")]
    db.session.add_all(fleets)
    db.session.commit()
    servers = [Server(name=name, url=f"https://{name}.test", authkey="K" * 40, fleet_id=fleets[0].id, user_id=user.id)
               for name in ("alpha", "beta", "gamma")]
    servers.append(Server(name="solo", url="https://solo.test", authkey="K" * 40, fleet_id=fleets[1].id,
                          user_id=user.id))
    db.session.add_all(servers)
    db.session.commit()
    yield {"user": user, "servers": servers, "fleets": fleets}
    for server in servers:
        db.session.delete(server)
    for item in fleets:
        redisClient.delete(f"fleet-org-findings:{item.id}")
        db.session.delete(item)
    db.session.commit()


@pytest.fixture()
def published(monkeypatch):
    """Server IDs whose health was published"""
    import application.models.health as healthModel
    calls = []
    monkeypatch.setattr(healthModel, "publishServerHealth", lambda server: calls.append(server.id))
    return calls


def orgs(**names):
    """`orgs(U1="CIRCL")` → records as a listing gives them"""
    return [{"uuid": globals()[key], "name": name} for key, name in names.items()]


# Findings

def test_a_fleet_that_lines_up_has_no_findings(digests):
    assert digests.computeFindings({1: {U1: "CIRCL", U2: "ACME"}, 2: {U1: "circl ", U2: "ACME"}, 3: {U2: "ACME"}}) \
        == {}


def test_other_uuid_and_renamed(digests):
    findings = digests.computeFindings({1: {U1: "CIRCL", U2: "ACME"}, 2: {U3: "circl", U2: "ACME Corp"}})
    assert findings[1][U1]["other_uuid"] == [[2, U3]]
    assert findings[2][U3]["other_uuid"] == [[1, U1]]
    assert findings[1][U2]["renamed"] == [[2, "ACME Corp"]]
    assert findings[2][U2]["renamed"] == [[1, "ACME"]]
    assert findings[1][U1]["name"] == "CIRCL"


def test_a_copy_made_by_sync_is_seen_from_both_sides(digests):
    """Server 2 had its own CIRCL (U3) when sync brought U1: MISP created `CIRCL_4821`"""
    findings = digests.computeFindings({1: {U1: "CIRCL"}, 2: {U3: "CIRCL", U1: "CIRCL_4821"}})
    assert findings[1][U1]["split_there"] == [[2, "CIRCL_4821", U3]]
    assert findings[1][U1]["renamed"] == [] and findings[1][U1]["other_uuid"] == []
    assert findings[2][U1]["split_here"] == [[1, "CIRCL", U3]]
    assert findings[2][U3]["other_uuid"] == [[1, U1]]


def test_findings_match_the_tabs_comparison(digests):
    """Same verdicts as the Organisations tab: `split_*` are `renamed` there"""
    from application.models import organisations
    rng = random.Random(7)
    uuids = [f"22222222-0000-4000-8000-{i:012d}" for i in range(8)]
    names = ["CIRCL", "circl", "ACME", "Acme  Corp", "Beta", "Gamma"]
    for _ in range(200):
        fleetDigests = {sid: {uuid: rng.choice(names) for uuid in rng.sample(uuids, rng.randint(0, 6))}
                        for sid in range(1, rng.randint(2, 5))}
        findings = digests.computeFindings(fleetDigests)
        for sid, own in fleetDigests.items():
            ownList = organisations.parse([{"uuid": uuid, "name": name} for uuid, name in own.items()])
            others = {other: organisations.parse([{"uuid": uuid, "name": name} for uuid, name in theirs.items()])
                      for other, theirs in fleetDigests.items() if other != sid}
            expected = organisations.compare(ownList, others)
            for uuid in own:
                found = findings.get(sid, {}).get(uuid, {})
                renamed = sorted(found.get("renamed", []) +
                                 [entry[:2] for entry in found.get("split_there", []) + found.get("split_here", [])])
                assert renamed == sorted(expected[uuid]["renamed"]), (fleetDigests, sid, uuid)
                assert sorted(found.get("other_uuid", [])) == sorted(expected[uuid]["other_uuid"]), \
                    (fleetDigests, sid, uuid)


# Digests and their cache

def test_digest_kept_and_rewritten_only_when_it_changes(fleet, digests, published):
    from application import redisClient
    alpha = fleet["servers"][0]
    assert digests.remember(alpha, orgs(U1="CIRCL"), now=100) is True
    assert digests.readDigest(alpha)["names"] == {U1: "CIRCL"}
    assert 0 < redisClient.ttl(digests.digestKey(alpha)) <= digests.DIGEST_SECONDS
    assert digests.remember(alpha, orgs(U1="CIRCL"), now=200) is False
    assert digests.readDigest(alpha)["fetched_at"] == 200
    assert digests.remember(alpha, orgs(U1="CIRCL", U2="ACME"), now=300) is True


def test_findings_are_cached_until_a_digest_changes(fleet, digests, published, monkeypatch):
    alpha, beta, gamma, solo = fleet["servers"]
    fleet_id = fleet["fleets"][0].id
    digests.remember(alpha, orgs(U1="CIRCL"))
    digests.remember(beta, orgs(U3="CIRCL"))
    computed = []
    original = digests.computeFindings
    monkeypatch.setattr(digests, "computeFindings", lambda found: computed.append(1) or original(found))

    first = digests.fleetFindings(fleet_id)
    assert first["findings"][alpha.id][U1]["other_uuid"] == [[beta.id, U3]]
    assert first["compared"] == sorted([alpha.id, beta.id]) and first["servers"][beta.id] == "beta"
    assert digests.fleetFindings(fleet_id) == first and computed == []  # Stored when beta's digest changed

    digests.remember(beta, orgs(U3="CIRCL"))  # Listed again, same organisations
    assert digests.fleetFindings(fleet_id) == first and computed == []

    digests.remember(beta, orgs(U1="CIRCL"))
    assert computed == [1] and digests.fleetFindings(fleet_id)["findings"] == {}


def test_findings_follow_servers_leaving_the_fleet(fleet, digests, published, db):
    alpha, beta, gamma, solo = fleet["servers"]
    digests.remember(alpha, orgs(U1="CIRCL"))
    digests.remember(beta, orgs(U3="CIRCL"))
    assert digests.fleetFindings(fleet["fleets"][0].id)["findings"]
    beta.fleet_id = fleet["fleets"][1].id
    db.session.commit()
    assert digests.fleetFindings(fleet["fleets"][0].id)["findings"] == {}


def test_a_change_publishes_the_servers_whose_findings_changed(fleet, digests, published):
    alpha, beta, gamma, solo = fleet["servers"]
    digests.remember(alpha, orgs(U1="CIRCL"))
    digests.remember(gamma, orgs(U2="ACME"))
    published.clear()

    digests.remember(beta, orgs(U3="CIRCL"))
    assert sorted(published) == sorted([alpha.id, beta.id])  # gamma has nothing to do with it

    published.clear()
    digests.remember(beta, orgs(U1="CIRCL"), publish_self=False)
    assert published == [alpha.id]

    published.clear()
    digests.remember(beta, orgs(U1="CIRCL"))
    assert published == []


def test_listings_of_the_tab_leave_a_digest(fleet, digests, published, monkeypatch):
    from application.models import mispOps, organisations
    alpha = fleet["servers"][0]
    monkeypatch.setattr(mispOps, "mispGetRequest",
                        lambda server, url, *args, **kwargs: listing(org(1, U1, "CIRCL"), org(2, U2, "ACME")))
    organisations.organisationsOf(alpha, refresh=True)
    assert digests.readDigest(alpha)["names"] == {U1: "CIRCL", U2: "ACME"}


def test_deleting_a_server_forgets_its_digest(fleet, digests, published, db):
    from application.DBModels import Server
    from application import redisModel
    solo = fleet["servers"][3]
    digests.remember(solo, orgs(U1="CIRCL"))
    redisModel.deleteServerData(solo.uuid, solo.id)
    assert digests.readDigest(solo) is None


# Health rule

def issuesOf(server, rule="organisation_mismatch"):
    from application.health import Context, evaluate_server
    snapshot = {"timestamp": 1, "query_result": {}}
    status = {"version": "2.5.1", "_latency": 0.1, "_status_code": 200, "timestamp": 1}
    return [issue for issue in evaluate_server(server, Context(now=2), snapshot=snapshot, status=status,
                                               track_first_seen=False) if issue.rule == rule]


def test_rule_warns_about_another_uuid(fleet, digests, published):
    alpha, beta, gamma, solo = fleet["servers"]
    digests.remember(alpha, orgs(U1="CIRCL", U2="ACME"))
    digests.remember(beta, orgs(U3="CIRCL", U2="ACME"))
    digests.remember(gamma, orgs(U4="CIRCL", U2="ACME"))
    [issue] = issuesOf(alpha)
    assert issue.id == f"organisation_mismatch:{alpha.id}:{U1}" and issue.subject == U1
    assert issue.severity == "warning" and issue.category == "sync"
    assert issue.title == "Organisation “CIRCL” has another UUID on 2 servers"
    assert issue.detail.startswith(f"beta: another UUID ({U3[:8]}…); gamma: another UUID ({U4[:8]}…). MISP matches")
    assert issue.action == {"kind": "open_tab", "target": "organisations", "uuid": U1}
    assert [entry["server"] for entry in issue.evidence["servers"]] == ["beta", "gamma"]


def test_rule_tells_a_copy_made_by_sync(fleet, digests, published):
    alpha, beta, gamma, solo = fleet["servers"]
    digests.remember(alpha, orgs(U1="CIRCL"))
    digests.remember(beta, orgs(U3="CIRCL", U1="CIRCL_4821"))
    [issue] = issuesOf(alpha)
    assert issue.severity == "warning" and issue.title == "Organisation “CIRCL” has another UUID on beta"
    assert issue.detail.startswith(f"beta: named “CIRCL_4821”, next to another “CIRCL” ({U3[:8]}…). Sync created")
    copyIssue, ownIssue = sorted(issuesOf(beta), key=lambda issue: issue.title)
    assert copyIssue.subject == U1 and copyIssue.severity == "warning"
    assert "which is another organisation here" in copyIssue.detail
    assert ownIssue.subject == U3 and ownIssue.severity == "warning"


def test_rule_only_informs_about_another_name(fleet, digests, published):
    alpha, beta, gamma, solo = fleet["servers"]
    digests.remember(alpha, orgs(U2="ACME"))
    digests.remember(beta, orgs(U2="ACME Corp"))
    [issue] = issuesOf(alpha)
    assert issue.severity == "info" and issue.title == "Organisation “ACME” has another name on beta"
    assert issue.detail == "beta: named “ACME Corp”. Sync matches organisations by UUID and keeps each server's name."


def test_rule_needs_the_servers_own_listing(fleet, digests, published):
    alpha, beta, gamma, solo = fleet["servers"]
    digests.remember(beta, orgs(U3="CIRCL"))
    digests.remember(gamma, orgs(U1="CIRCL"))
    assert issuesOf(alpha) == []
    digests.remember(solo, orgs(U1="CIRCL"))
    assert issuesOf(solo) == []


# Full refresh

REFRESH_ANSWERS = {
    "/servers/serverSettings/diagnostics/light:1": {"finalSettings": []},
    "/users/view/me": {"User": {"id": "1"}},
    "/servers/index": [],
    "/users/registrations": [],
    "/users/statistics": {"stats": {}},
    INDEX: [org(1, U1, "CIRCL")],
}


@pytest.fixture()
def refreshed(monkeypatch):
    """Runs a full refresh with canned answers; returns the URLs asked"""
    from application import redisModel
    import application.models.servers as serverModel
    requested = []
    answers = copy.deepcopy(REFRESH_ANSWERS)

    async def fakeFetcher(server, urls, timeout=300):
        requested.extend(urls)
        return [copy.deepcopy(answers[url]) for url in urls]
    monkeypatch.setattr(serverModel, "asyncFetcher", fakeFetcher)
    monkeypatch.setattr(redisModel, "setServerWatchedTimestamp", lambda uuid: None)

    def run(server):
        requested.clear()
        asyncio.run(serverModel.fetchServerInfoAsync(server, {}))
        return list(requested)
    run.answers = answers
    return run


def test_full_refresh_lists_organisations_only_with_another_server_to_compare(fleet, digests, published, refreshed):
    from application.models import organisations
    alpha, beta, gamma, solo = fleet["servers"]
    assert INDEX not in refreshed(solo)
    assert digests.readDigest(solo) is None

    assert refreshed(alpha).count(INDEX) == 1
    assert digests.readDigest(alpha)["names"] == {U1: "CIRCL"}
    assert [entry["uuid"] for entry in organisations.readCached(alpha)["organisations"]] == [U1]


def test_full_refresh_keeps_the_digest_when_the_listing_fails(fleet, digests, published, refreshed):
    alpha = fleet["servers"][0]
    refreshed(alpha)
    refreshed.answers[INDEX] = {"error": "Timeout Exception (300s)"}
    refreshed(alpha)
    assert digests.readDigest(alpha)["names"] == {U1: "CIRCL"}


def test_full_refresh_asks_once_when_the_baseline_needs_organisations(fleet, digests, published, refreshed,
                                                                       monkeypatch):
    from application.models import baselineDrift
    alpha = fleet["servers"][0]
    monkeypatch.setattr(baselineDrift, "contentPlanOfFleet", lambda fleet_id: baselineDrift.ContentPlan(["organisation"]))
    assert refreshed(alpha).count(INDEX) == 1
    assert digests.readDigest(alpha)["names"] == {U1: "CIRCL"}
