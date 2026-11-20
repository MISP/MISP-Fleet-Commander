"""Saved queries: statements a user keeps, run by hand or on a schedule as ordinary query runs, each server's last
answer kept and checked against what the saved query expects, and the health issues that follow.

A saved query's runs go through the same unit as any query run, so a server without complex queries is never
searched by one either (its WHERE would be dropped, and the answer read as a match)."""
import time

import pytest

from test_fleet_queries import (FakeResponse, ROLE_WITHOUT, caps, fleet, misp, queued, recorded,  # noqa: F401
                                searches, supportAnswer)

COUNT = "SELECT COUNT(*) FROM attributes WHERE value = '198.51.100.23'"
SELECT = "SELECT * FROM attributes WHERE value = '198.51.100.23' LIMIT 100"


def countAnswer(number):
    return 200, str(number), {'Content-Type': 'text/plain; charset=UTF-8', 'X-Result-Count': str(number)}


@pytest.fixture()
def runs(monkeypatch):
    """Jobs run to their end as soon as they are queued, as the workers would"""
    import application.models.jobRunner as jobRunner
    from application.workers import tasks
    started = []

    def run(job_id):
        started.append(job_id)
        jobRunner.run(job_id, max_concurrency=3)
    monkeypatch.setattr(tasks, 'runJob', run)
    return started


@pytest.fixture()
def published(monkeypatch):
    """Servers whose health was published again"""
    from application.models import health
    servers = []
    monkeypatch.setattr(health, 'publishServerHealth', lambda server: servers.append(server.id))
    return servers


@pytest.fixture()
def alone(db):
    """Saved queries of earlier tests (the database lives for the session) are taken off their schedule, so that
    `runDue` starts only this test's"""
    from application.DBModels import SavedQuery
    SavedQuery.query.update({'schedule_minutes': None})
    db.session.commit()


def save(user, **fields):
    from application.models import savedQueries
    body = {'name': f'Query {time.time_ns()}', 'statement': COUNT, **fields}
    return savedQueries.create(user, body)


def watched(user, fleet, **fields):
    """A saved query on the fleet, every hour, expecting no match"""
    return save(user, fleet_id=fleet.id, schedule_minutes=60, expectation={'comparator': 'eq', 'value': 0},
                **fields)


def runSaved(saved):
    """A run of the saved query, to its end"""
    from application.models import savedQueries
    return savedQueries.startRun(saved)


def kept(saved):
    from application import db
    db.session.refresh(saved)
    return {result.server_id: result for result in saved.results}


def healthOf(server, now=None):
    """The server's `saved_query` issues, its connection test passing"""
    from application.health import Context, evaluate_server
    status = {'version': '3.0.0', '_latency': 0.2, '_status_code': 200, 'timestamp': int(time.time())}
    issues = evaluate_server(server, Context(now=now or int(time.time()), latest_release='3.0.0'), snapshot=None,
                             status=status, track_first_seen=False)
    return {issue.id: issue for issue in issues if issue.rule == 'saved_query'}


# Saving

def test_a_saved_query_is_checked_and_kept(db, client, auth_headers, fleet):
    user, fleetRow, servers = fleet
    answer = client.post('/queries/saved', headers=auth_headers(user), json={
        'name': '  No   bad IP ', 'description': 'Nobody holds it', 'statement': COUNT, 'fleet_id': fleetRow.id,
        'schedule_minutes': 60, 'expectation': {'comparator': 'eq', 'value': 0}, 'severity': 'critical'})
    assert answer.status_code == 201, answer.json
    saved = answer.json
    assert (saved['name'], saved['kind'], saved['fleet_name'], saved['server_count']) == \
        ('No bad IP', 'count', 'Query fleet', 3)
    assert (saved['expectation'], saved['expectation_text'], saved['severity']) == \
        ({'comparator': 'eq', 'value': 0}, 'exactly 0', 'critical')
    assert [s['server_name'] for s in saved['servers']] == ['misp-a', 'misp-b', 'misp-c']
    assert {s['state'] for s in saved['servers']} == {'not_run'} and saved['overview']['not_run'] == 3
    listed = client.get('/queries/saved', headers=auth_headers(user)).json['saved']
    assert [s['id'] for s in listed] == [saved['id']]


@pytest.mark.parametrize('fields, status, field', [
    ({'name': ''}, 400, 'name'),
    ({'statement': 'SELECT * FROM nowhere'}, 400, 'statement'),
    ({'statement': 'USE hub'}, 400, 'statement'),
    ({'fleet_id': None}, 400, 'target'),
    ({'server_ids': [1]}, 400, 'target'),  # both a fleet and servers
    ({'schedule_minutes': 7}, 400, 'schedule_minutes'),
    ({'statement': 'DESCRIBE events', 'schedule_minutes': 60}, 400, 'schedule_minutes'),
    ({'statement': 'DESCRIBE events', 'expectation': {'comparator': 'eq', 'value': 0}}, 400, 'expectation'),
    ({'statement': SELECT, 'expectation': {'comparator': 'lte', 'value': 5}}, 400, 'expectation'),
    ({'expectation': {'comparator': 'about', 'value': 5}}, 400, 'expectation'),
    ({'expectation': {'comparator': 'eq', 'value': -1}}, 400, 'expectation'),
    ({'expectation': {'comparator': 'eq', 'value': True}}, 400, 'expectation'),
    ({'severity': 'urgent'}, 400, 'severity'),
])
def test_what_cannot_be_saved(db, client, auth_headers, fleet, fields, status, field):
    user, fleetRow, _ = fleet
    body = {'name': 'q', 'statement': COUNT, 'fleet_id': fleetRow.id, **fields}
    answer = client.post('/queries/saved', headers=auth_headers(user), json=body)
    assert (answer.status_code, answer.json.get('field')) == (status, field), answer.json


def test_a_statement_mistake_is_placed_on_its_text(db, client, auth_headers, fleet):
    user, fleetRow, _ = fleet
    answer = client.post('/queries/saved', headers=auth_headers(user),
                         json={'name': 'q', 'statement': 'SELECT * FROM nowhere', 'fleet_id': fleetRow.id})
    [error] = answer.json['errors']
    assert 'SELECT * FROM nowhere'[error['start']:error['end']] == 'nowhere'


def test_select_expects_rows_or_none(db, fleet):
    from application.models import savedQueries
    user, fleetRow, _ = fleet
    none = save(user, statement=SELECT, fleet_id=fleetRow.id, expectation={'comparator': 'eq', 'value': 0})
    some = save(user, statement=SELECT, fleet_id=fleetRow.id, expectation={'comparator': 'gt', 'value': 0})
    assert savedQueries.serialize(none)['expectation_text'] == 'no rows'
    assert savedQueries.serialize(some)['expectation_text'] == 'some rows'


def test_names_are_unique_per_user(db, client, auth_headers, fleet, make_user):
    user, fleetRow, _ = fleet
    save(user, name='Bad IP', fleet_id=fleetRow.id)
    answer = client.post('/queries/saved', headers=auth_headers(user),
                         json={'name': 'bad ip', 'statement': COUNT, 'fleet_id': fleetRow.id})
    assert (answer.status_code, answer.json['field']) == (409, 'name')


def test_saved_queries_are_their_owners(db, client, auth_headers, fleet, make_user):
    user, fleetRow, servers = fleet
    other = make_user(f'other-{time.time_ns()}@test.local', is_admin=True)
    saved = save(user, fleet_id=fleetRow.id)
    headers = auth_headers(other)
    assert client.get(f'/queries/saved/{saved.id}', headers=headers).status_code == 404
    assert client.put(f'/queries/saved/{saved.id}', headers=headers, json={'name': 'x'}).status_code == 404
    assert client.delete(f'/queries/saved/{saved.id}', headers=headers).status_code == 404
    assert client.post(f'/queries/saved/{saved.id}/run', headers=headers).status_code == 404
    assert client.get('/queries/saved', headers=headers).json['saved'] == []
    # Nor can anyone aim one at another user's fleet or servers
    for target in ({'fleet_id': fleetRow.id}, {'server_ids': [servers[0].id]}):
        answer = client.post('/queries/saved', headers=headers, json={'name': 'x', 'statement': COUNT, **target})
        assert answer.status_code == 404


def test_a_new_statement_forgets_the_answers_a_new_expectation_does_not(db, fleet, misp, runs, published):
    from application.models import savedQueries
    user, fleetRow, servers = fleet
    misp['answers'][(None, 'POST', '/attributes/restSearch')] = countAnswer(3)
    saved = watched(user, fleetRow)
    runSaved(saved)
    assert {r.value for r in kept(saved).values()} == {3}
    states = {s['state'] for s in savedQueries.serialize(saved, withServers=True)['servers']}
    assert states == {'unmet'}
    savedQueries.update(user, saved.id, {'expectation': {'comparator': 'gte', 'value': 1}})
    assert {s['state'] for s in savedQueries.serialize(saved, withServers=True)['servers']} == {'met'}
    savedQueries.update(user, saved.id, {'statement': COUNT.replace('23', '24')})
    assert kept(saved) == {}


def test_a_scheduled_query_that_changes_runs_at_the_next_turn(db, fleet, queued):
    from application.models import savedQueries
    user, fleetRow, servers = fleet
    now = int(time.time())
    scheduled = watched(user, fleetRow)
    byHand = save(user, fleet_id=fleetRow.id)
    for saved in (scheduled, byHand):
        saved.last_run_at = now - 60
    db.session.commit()
    # A new name or expectation changes nothing of what runs
    savedQueries.update(user, scheduled.id, {'name': 'Renamed', 'expectation': {'comparator': 'lte', 'value': 2}})
    assert scheduled.last_run_at == now - 60 and not savedQueries.isDue(scheduled, now)
    for change in ({'statement': COUNT.replace('23', '24')}, {'server_ids': [servers[0].id]},
                   {'schedule_minutes': 1440}):
        scheduled.last_run_at = now - 60
        db.session.commit()
        savedQueries.update(user, scheduled.id, change)
        assert scheduled.last_run_at is None and savedQueries.isDue(scheduled, now), change
    # Run by hand only: its last run stays what it was
    savedQueries.update(user, byHand.id, {'statement': COUNT.replace('23', '25')})
    assert byHand.last_run_at == now - 60


def test_a_statement_that_cannot_be_scheduled_drops_nothing_silently(db, fleet):
    from application.models import savedQueries
    user, fleetRow, _ = fleet
    saved = watched(user, fleetRow)
    with pytest.raises(savedQueries.SavedQueryError) as refused:
        savedQueries.update(user, saved.id, {'statement': 'DESCRIBE events'})
    assert refused.value.field == 'schedule_minutes'
    db.session.rollback()
    savedQueries.update(user, saved.id, {'statement': 'DESCRIBE events', 'schedule_minutes': None,
                                         'expectation': None})
    assert savedQueries.serialize(saved)['kind'] == 'describe'


# Runs

def test_a_run_is_a_query_job_of_the_owner_and_keeps_each_answer(db, client, auth_headers, fleet, misp, runs,
                                                                  published):
    user, fleetRow, servers = fleet
    saved = watched(user, fleetRow)
    misp['answers'][(None, 'POST', '/attributes/restSearch')] = countAnswer(0)
    misp['answers'][(servers[1].url, 'POST', '/attributes/restSearch')] = countAnswer(4)
    misp['answers'][(servers[2].url, 'GET', '/attributes/queryDescribe')] = supportAnswer('not_supported')
    answer = client.post(f'/queries/saved/{saved.id}/run', headers=auth_headers(user))
    assert answer.status_code == 202
    from application.DBModels import Job
    job = db.session.get(Job, answer.json['job_id'])
    assert (job.kind, job.user_id, job.params['saved_query_id']) == ('mispql_query', user.id, saved.id)
    assert job.title == f'Saved query “{saved.name}” on 3 servers'
    results = kept(saved)
    assert {servers[0].id: (results[servers[0].id].outcome, results[servers[0].id].value),
            servers[1].id: (results[servers[1].id].outcome, results[servers[1].id].value),
            servers[2].id: (results[servers[2].id].outcome, results[servers[2].id].value)} == {
        servers[0].id: ('count', 0), servers[1].id: ('count', 4), servers[2].id: ('not_supported', None)}
    assert results[servers[1].id].job_id == job.id and results[servers[1].id].message == 'Count: 4'
    assert sorted(published) == sorted(s.id for s in servers)
    view = client.get(f'/queries/saved/{saved.id}', headers=auth_headers(user)).json
    assert {s['server_name']: s['state'] for s in view['servers']} == \
        {'misp-a': 'unmet', 'misp-b': 'met', 'misp-c': 'unchecked'}
    assert (view['last_job_id'], view['last_job_status'], view['running']) == (job.id, 'done', False)
    assert view['overview'] == {'met': 1, 'unmet': 1, 'unchecked': 1, 'not_run': 0, 'answered': 0}


def test_rows_are_never_kept_with_the_saved_query(db, fleet, misp, runs, published):
    user, fleetRow, servers = fleet
    misp['answers'][(None, 'POST', '/attributes/restSearch')] = recorded('rows_attributes')
    saved = save(user, statement=SELECT, server_ids=[servers[0].id], schedule_minutes=60,
                 expectation={'comparator': 'eq', 'value': 0})
    runSaved(saved)
    result = kept(saved)[servers[0].id]
    assert (result.outcome, result.value, result.more) == ('rows', 1, False)
    assert set(vars(result)) & {'rows', 'columns'} == set()


def test_a_run_is_refused_while_one_is_going(db, client, auth_headers, fleet, queued):
    user, fleetRow, _ = fleet
    saved = watched(user, fleetRow)
    assert client.post(f'/queries/saved/{saved.id}/run', headers=auth_headers(user)).status_code == 202
    answer = client.post(f'/queries/saved/{saved.id}/run', headers=auth_headers(user))
    assert answer.status_code == 409


def test_a_run_by_hand_is_refused_when_the_statement_no_longer_passes(db, client, auth_headers, fleet, caps, queued):
    user, fleetRow, _ = fleet
    saved = save(user, statement=SELECT, fleet_id=fleetRow.id)
    caps['query_max_limit'] = 50
    answer = client.post(f'/queries/saved/{saved.id}/run', headers=auth_headers(user))
    assert answer.status_code == 400 and answer.json['errors'][0]['message'].startswith('At most 50 rows')
    assert queued == []


def test_an_old_run_retried_does_not_overwrite_a_new_statement(db, fleet, misp, runs, published):
    import application.models.userJobs as userJobs
    from application.models import savedQueries
    user, fleetRow, servers = fleet
    misp['answers'][(None, 'POST', '/attributes/restSearch')] = countAnswer(2)
    saved = watched(user, fleetRow)
    job = runSaved(saved)
    savedQueries.update(user, saved.id, {'statement': COUNT.replace('23', '24')})
    userJobs.retry(user, job.id, only_failed=False)
    assert kept(saved) == {}


def test_a_retry_of_the_current_statement_is_kept(db, fleet, misp, runs, published):
    import application.models.userJobs as userJobs
    user, fleetRow, servers = fleet
    misp['answers'][(None, 'POST', '/attributes/restSearch')] = {'error': 'Server unreachable'}
    saved = watched(user, fleetRow)
    job = runSaved(saved)
    assert {r.outcome for r in kept(saved).values()} == {'unreachable'}
    misp['answers'][(None, 'POST', '/attributes/restSearch')] = countAnswer(0)
    retry = userJobs.retry(user, job.id)
    assert {(r.outcome, r.job_id) for r in kept(saved).values()} == {('count', retry.id)}


def test_an_older_answer_does_not_replace_a_newer_one(db, fleet, misp, runs, published):
    from application.models import savedQueries
    user, fleetRow, servers = fleet
    misp['answers'][(None, 'POST', '/attributes/restSearch')] = countAnswer(1)
    saved = watched(user, fleetRow)
    old = runSaved(saved)
    for result in old.results:
        result.finished -= 100
    misp['answers'][(None, 'POST', '/attributes/restSearch')] = countAnswer(0)
    runSaved(saved)
    db.session.commit()
    assert savedQueries.recordRun(old) == []
    assert {r.value for r in kept(saved).values()} == {0}


def test_a_unit_cancelled_before_it_started_leaves_the_kept_answer(db, fleet, misp, runs, published):
    import application.models.jobRunner as jobRunner
    import application.models.jobs as jobModel
    user, fleetRow, servers = fleet
    misp['answers'][(None, 'POST', '/attributes/restSearch')] = countAnswer(0)
    saved = watched(user, fleetRow)
    runSaved(saved)
    before = {serverId: r.job_id for serverId, r in kept(saved).items()}
    job = jobModel.create(user, 'mispql_query', servers, title='t',
                          params={'statement': saved.statement, 'saved_query_id': saved.id})
    jobRunner.requestCancel(job.id)
    jobRunner.run(job.id)
    assert {r.status for r in job.results} == {'cancelled'}
    assert {serverId: r.job_id for serverId, r in kept(saved).items()} == before


# The gate: a saved query searches no server that has not just shown it runs complex queries

@pytest.mark.parametrize('check, role, outcome', [
    (supportAnswer('not_supported'), None, 'not_supported'),
    (supportAnswer('no_permission'), ROLE_WITHOUT, 'no_permission'),
    (supportAnswer('no_permission'), None, 'unavailable'),
    ((500, '<pre class="cake-error">Warning</pre>'), None, 'unknown'),
    ({'error': 'Server unreachable'}, None, 'unreachable'),
])
@pytest.mark.parametrize('statement', [COUNT, SELECT])
def test_a_scheduled_run_searches_no_server_without_complex_queries(db, alone, fleet, misp, runs, published, check,
                                                                    role, outcome, statement):
    from application import redisModel
    from application.models import queryCapability, savedQueries
    user, fleetRow, servers = fleet
    server = servers[0]
    # Whatever its cached capability and snapshot say
    queryCapability.remember(server, queryCapability.capability('supported', 200, ''))
    if role is not None:
        redisModel.saveServerInfo(server.uuid, {'timestamp': 1, 'query_result': {'serverUser': {'Role': role}}})
    misp['answers'][(server.url, 'GET', '/attributes/queryDescribe')] = check
    # What such a server would answer if searched: everything, as if there were no WHERE
    misp['answers'][(server.url, 'POST', '/attributes/restSearch')] = countAnswer(3_900_000)
    saved = save(user, statement=statement, server_ids=[server.id], schedule_minutes=15,
                 expectation={'comparator': 'eq', 'value': 0})
    assert savedQueries.runDue() == [saved.last_job_id]
    assert searches(misp, server.url) == []
    result = kept(saved)[server.id]
    assert (result.outcome, result.value) == (outcome, None)
    assert set(healthOf(server)) == {f'saved_query:{server.id}:{saved.id}:unchecked'}


# Schedule

def test_due_saved_queries_start_on_their_schedule(db, alone, fleet, queued):
    from application.models import savedQueries
    user, fleetRow, _ = fleet
    now = int(time.time())
    due = watched(user, fleetRow)
    byHand = save(user, fleet_id=fleetRow.id)
    later = watched(user, fleetRow)
    later.last_run_at = now - 30 * 60
    db.session.commit()
    assert savedQueries.runDue(now) == [due.last_job_id] and queued == [due.last_job_id]
    assert (due.last_run_at, byHand.last_run_at, later.last_run_at) == (now, None, now - 30 * 60)
    # An hour on: `later` is due, and so is `due`, but its run is still going: it waits for it
    first = due.last_job_id
    assert savedQueries.runDue(now + 3600) == [later.last_job_id]
    assert due.last_job_id == first


def test_a_lost_run_does_not_hold_the_schedule_forever(db, alone, fleet, queued):
    from application.DBModels import Job
    from application.models import savedQueries
    user, fleetRow, _ = fleet
    saved = watched(user, fleetRow)
    now = int(time.time())
    savedQueries.runDue(now)
    stuck = db.session.get(Job, saved.last_job_id)
    stuck.created = now - savedQueries.LOST_RUN_SECONDS - 1
    db.session.commit()
    assert savedQueries.runDue(now + 3600) == [saved.last_job_id]
    assert saved.last_job_id != stuck.id


def test_scheduled_runs_can_be_turned_off(db, alone, fleet, queued, monkeypatch):
    from application.models import savedQueries
    from application.models import setting as settingModel
    user, fleetRow, _ = fleet
    saved = watched(user, fleetRow)
    original = settingModel.getRefreshValue
    monkeypatch.setattr(settingModel, 'getRefreshValue',
                        lambda name: False if name == 'query_schedule_enabled' else original(name))
    assert savedQueries.runDue() == [] and saved.last_run_at is None
    assert savedQueries.serialize(saved)['next_run_at'] is None


def test_a_saved_query_with_no_server_left_says_so_and_waits(db, alone, fleet, queued):
    from application.DBModels import Server
    from application.models import savedQueries
    user, fleetRow, servers = fleet
    saved = save(user, server_ids=[servers[0].id], schedule_minutes=60,
                 expectation={'comparator': 'eq', 'value': 0})
    db.session.delete(db.session.get(Server, servers[0].id))
    db.session.commit()
    now = int(time.time())
    assert savedQueries.runDue(now) == []
    db.session.refresh(saved)
    assert (saved.last_run_at, saved.last_error, saved.last_job_id) == \
        (now, 'None of its servers exist anymore', None)
    # Tried again at the next turn of its schedule, not every minute
    assert savedQueries.runDue(now + 60) == [] and saved.last_run_at == now


def test_deleting_the_fleet_keeps_its_saved_queries_without_target(db, fleet, misp, runs, published):
    from application.DBModels import Fleet, SavedQueryResult
    from application.models import savedQueries
    user, fleetRow, servers = fleet
    misp['answers'][(None, 'POST', '/attributes/restSearch')] = countAnswer(0)
    saved = watched(user, fleetRow)
    runSaved(saved)
    db.session.delete(db.session.get(Fleet, fleetRow.id))
    db.session.commit()
    db.session.refresh(saved)
    assert (saved.fleet_id, saved.server_ids) == (None, None)
    assert SavedQueryResult.query.filter_by(saved_query_id=saved.id).count() == 0  # its servers went with it
    data = savedQueries.serialize(saved)
    assert (data['server_count'], data['last_error']) == (0, 'Its fleet was deleted: choose where it runs')
    with pytest.raises(savedQueries.SavedQueryError) as refused:
        savedQueries.runNow(user, saved.id)
    assert refused.value.status == 409


def test_deleting_the_owner_deletes_their_saved_queries(db, fleet, make_user):
    from application.DBModels import SavedQuery
    from application.models import users
    owner = make_user(f'gone-{time.time_ns()}@test.local')
    _, fleetRow, servers = fleet
    from application.DBModels import Fleet
    own = Fleet(name='Own', description='', user_id=owner.id, timestamp=1)
    db.session.add(own)
    db.session.commit()
    saved = save(owner, fleet_id=own.id)
    savedId = saved.id
    users.delete(owner.id)
    assert db.session.get(SavedQuery, savedId) is None


# Health

def test_an_unmet_expectation_is_an_issue_of_the_saved_query_severity(db, fleet, misp, runs, published):
    user, fleetRow, servers = fleet
    misp['answers'][(None, 'POST', '/attributes/restSearch')] = countAnswer(0)
    misp['answers'][(servers[0].url, 'POST', '/attributes/restSearch')] = countAnswer(12)
    saved = watched(user, fleetRow, severity='critical', description='Nobody should hold this IP')
    runSaved(saved)
    issues = healthOf(servers[0])
    issue = issues[f'saved_query:{servers[0].id}:{saved.id}']
    assert (issue.severity, issue.category) == ('critical', 'queries')
    assert issue.title == f'Saved query “{saved.name}”: expected exactly 0, counted 12'
    assert issue.detail == 'Nobody should hold this IP.'
    assert issue.action == {'kind': 'open_saved_query', 'saved_query_id': saved.id}
    assert (issue.evidence['value'], issue.evidence['statement']) == (12, COUNT)
    assert healthOf(servers[1]) == {}


def test_rows_found_or_not_in_words(db, fleet, misp, runs, published):
    user, fleetRow, servers = fleet
    misp['answers'][(None, 'POST', '/attributes/restSearch')] = recorded('rows_attributes')
    saved = save(user, statement=SELECT, server_ids=[servers[0].id], schedule_minutes=60,
                 expectation={'comparator': 'eq', 'value': 0})
    runSaved(saved)
    [issue] = healthOf(servers[0]).values()
    assert issue.title.endswith('expected no rows, found 1 row')
    assert issue.detail == f"Runs {SELECT}."


def test_only_scheduled_saved_queries_with_an_expectation_raise_issues(db, fleet, misp, runs, published):
    from application.models import savedQueries
    user, fleetRow, servers = fleet
    misp['answers'][(None, 'POST', '/attributes/restSearch')] = countAnswer(5)
    byHand = save(user, fleet_id=fleetRow.id, expectation={'comparator': 'eq', 'value': 0})
    noExpectation = save(user, fleet_id=fleetRow.id, schedule_minutes=60)
    runSaved(byHand)
    runSaved(noExpectation)
    assert healthOf(servers[0]) == {}
    assert {s['state'] for s in savedQueries.serialize(noExpectation, withServers=True)['servers']} == {'answered'}
    savedQueries.update(user, byHand.id, {'schedule_minutes': 60})
    assert set(healthOf(servers[0])) == {f'saved_query:{servers[0].id}:{byHand.id}'}


def test_a_server_no_longer_aimed_at_has_no_issue(db, fleet, misp, runs, published):
    from application.DBModels import Fleet
    user, fleetRow, servers = fleet
    misp['answers'][(None, 'POST', '/attributes/restSearch')] = countAnswer(5)
    saved = watched(user, fleetRow)
    runSaved(saved)
    assert len(healthOf(servers[0])) == 1
    elsewhere = Fleet(name='Elsewhere', description='', user_id=user.id, timestamp=1)
    db.session.add(elsewhere)
    db.session.commit()
    servers[0].fleet_id = elsewhere.id
    db.session.commit()
    assert healthOf(servers[0]) == {}


def test_query_errors_are_an_info_issue_of_their_own(db, fleet, misp, runs, published):
    user, fleetRow, servers = fleet
    misp['answers'][(None, 'POST', '/attributes/restSearch')] = recorded('error_several')
    saved = watched(user, fleetRow)
    runSaved(saved)
    [issue] = healthOf(servers[0]).values()
    assert (issue.id, issue.severity, issue.title) == (
        f'saved_query:{servers[0].id}:{saved.id}:unchecked', 'info', f'Saved query “{saved.name}” could not run')
    assert issue.detail.startswith('4 errors in the query') and issue.detail.endswith('not checked on this server.')


def test_issues_reach_the_owner_through_the_health_api(db, client, auth_headers, fleet, misp, runs, published,
                                                       monkeypatch, make_user):
    from application import redisModel
    from application.health import versions
    monkeypatch.setattr(versions, 'latest_release', lambda *args, **kwargs: '3.0.0')
    user, fleetRow, servers = fleet
    for server in servers:
        redisModel.saveServerStatus(server.uuid, {'version': '3.0.0', '_latency': 0.2, '_status_code': 200,
                                                  'timestamp': int(time.time())})
    misp['answers'][(None, 'POST', '/attributes/restSearch')] = countAnswer(5)
    saved = watched(user, fleetRow)
    runSaved(saved)
    issues = client.get(f'/health/issues?fleet_id={fleetRow.id}&category=queries',
                        headers=auth_headers(user)).json
    assert sorted(i['id'] for i in issues) == sorted(f'saved_query:{s.id}:{saved.id}' for s in servers)
    other = make_user(f'other-{time.time_ns()}@test.local', is_admin=True)
    assert client.get('/health/issues?category=queries', headers=auth_headers(other)).json == []


def test_deleting_a_server_forgets_its_answers(db, fleet, misp, runs, published):
    from application.DBModels import SavedQueryResult, Server
    user, fleetRow, servers = fleet
    misp['answers'][(None, 'POST', '/attributes/restSearch')] = countAnswer(0)
    saved = watched(user, fleetRow)
    runSaved(saved)
    db.session.delete(db.session.get(Server, servers[0].id))
    db.session.commit()
    assert {r.server_id for r in SavedQueryResult.query.filter_by(saved_query_id=saved.id)} == \
        {servers[1].id, servers[2].id}


def test_the_language_says_what_a_saved_query_may_hold(db, client, auth_headers, fleet):
    user, _, _ = fleet
    saved = client.get('/queries/language', headers=auth_headers(user)).json['saved']
    assert [s['minutes'] for s in saved['schedules']] == [15, 60, 360, 720, 1440]
    assert [c['name'] for c in saved['comparators']] == ['eq', 'ne', 'lt', 'lte', 'gt', 'gte']
    assert saved['row_expectations'] == [{'comparator': 'eq', 'value': 0, 'label': 'no rows'},
                                         {'comparator': 'gt', 'value': 0, 'label': 'some rows'}]
    assert saved['scheduled_runs'] is True
