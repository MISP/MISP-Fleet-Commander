"""Fleet queries: a MispQL statement checked, run on many servers as a job, each server's answer read and kept.

A MISP without complex queries drops a search's WHERE and answers as if there were none, so the tests here make sure
that no search reaches a server that has not just shown it runs them: on a run, on a retry, whatever its cached
capability or snapshot says. MISP's answers come from live recordings (fixtures/misp_query_answers.json,
fixtures/misp_support_check.json)."""
import json
import uuid
from pathlib import Path

import pytest
import requests

FIXTURES = Path(__file__).parent / 'fixtures'
ANSWERS = json.loads((FIXTURES / 'misp_query_answers.json').read_text())
SUPPORT = json.loads((FIXTURES / 'misp_support_check.json').read_text())
ROLE_WITHOUT = {'id': '3', 'name': 'User', 'perm_site_admin': False, 'perm_complex_query': False}
ROLE_WITH = {'id': '7', 'name': 'MispQL', 'perm_site_admin': False, 'perm_complex_query': True}


class FakeResponse:
    def __init__(self, status_code, content, headers=None):
        self.status_code = status_code
        self.content = content if isinstance(content, bytes) else content.encode()
        self.headers = headers or {'Content-Type': 'application/json'}


def recorded(name):
    """(status, body, headers) of a recorded answer"""
    answer = ANSWERS[name]
    body = answer['body']
    return answer['status'], json.dumps(body) if not isinstance(body, str) else body, dict(answer['headers'])


def supportAnswer(name):
    return SUPPORT[name]['status'], json.dumps(SUPPORT[name]['body'])


@pytest.fixture()
def caps(monkeypatch):
    """Settings as the tests set them; the defaults otherwise"""
    from application.models import setting as settingModel
    values = {}
    original = settingModel.intValue
    monkeypatch.setattr(settingModel, 'intValue', lambda name: values.get(name, original(name)))
    return values


@pytest.fixture()
def misp(monkeypatch, caps):
    """Fake MISP servers. `answers[(url or None, method, path)]` is (status, body[, headers]), an error dict, or a
    function of the request body giving one; the support check answers 200 by default. Every request is kept in
    `requests` as (server url, method, path, body)"""
    from application.models import fleetQueries, queryCapability
    state = {'answers': {(None, 'GET', '/attributes/queryDescribe'): supportAnswer('supported')}, 'requests': []}

    def fake(server, method, url, data=None, timeout=None, max_bytes=None):
        state['requests'].append((server.url, method, url, data))
        answer = state['answers'].get((server.url, method, url), state['answers'].get((None, method, url)))
        if callable(answer):
            answer = answer(data)
        if answer is None:
            return FakeResponse(404, b'{"name": "Not Found", "message": "Not Found"}')
        return answer if isinstance(answer, dict) else FakeResponse(*answer)
    monkeypatch.setattr(fleetQueries, 'mispRawRequest', fake)
    monkeypatch.setattr(queryCapability, 'mispRawRequest', fake)
    return state


def searches(state, url=None):
    return [r for r in state['requests'] if r[2].endswith('/restSearch') and (url is None or r[0] == url)]


@pytest.fixture()
def fleet(db, make_user):
    from application import redisModel
    from application.DBModels import Fleet, Server
    user = make_user(f'query-{uuid.uuid4().hex[:8]}@test.local')
    fleet = Fleet(name='Query fleet', description='', user_id=user.id, timestamp=1)
    db.session.add(fleet)
    db.session.commit()
    servers = []
    for name in ('misp-b', 'misp-a', 'misp-c'):
        server = Server(name=name, url=f'https://{name}.test/', user_id=user.id, fleet_id=fleet.id)
        server.authkey = f'key-{name}'
        db.session.add(server)
        servers.append(server)
    db.session.commit()
    yield user, fleet, servers
    for server in servers:
        redisModel.deleteServerData(server.uuid, server.id)


def runQuery(user, servers, statement):
    """Create and run a query job to its end, as the workers would"""
    import application.models.jobRunner as jobRunner
    import application.models.jobs as jobModel
    job = jobModel.create(user, 'mispql_query', servers, params={'statement': statement}, title='test')
    jobRunner.run(job.id, max_concurrency=3)
    return job


def summaryOf(job, server):
    [result] = [r for r in job.results if r.server_id == server.id]
    return result


# Checking a statement

def test_a_statement_is_checked_and_capped(app, caps):
    from application.models import fleetQueries
    caps['query_max_limit'] = 500
    prepared = fleetQueries.prepare("SELECT value, tags FROM attributes WHERE type = 'ip-dst'")
    assert (prepared.kind, prepared.table, prepared.limit, prepared.limit_added) == ('select', 'attributes', 500, True)
    assert (prepared.plan.body['limit'], prepared.plan.body['page']) == (500, 1)
    assert prepared.columns == ['value', 'Tag'] and prepared.defaultColumns() == ['value', 'Tag']
    kept = fleetQueries.prepare('SELECT * FROM events WHERE id > 0 LIMIT 500')
    assert (kept.limit, kept.limit_added, kept.plan.body['metadata']) == (500, False, 1)
    assert kept.defaultColumns()[:3] == ['id', 'date', 'info']
    assert fleetQueries.prepare('SELECT * FROM events LIMIT 5 FORMAT flat').defaultColumns() is None
    assert fleetQueries.prepare('SELECT COUNT(*) FROM events WHERE id > 0').kind == 'count'
    assert fleetQueries.prepare('DESCRIBE events').kind == 'describe'
    assert fleetQueries.prepare('SHOW TABLES;').kind == 'show_tables'


def located(text, needle, occurrence=0):
    start = -1
    for _ in range(occurrence + 1):
        start = text.index(needle, start + 1)
    return start, start + len(needle)


@pytest.mark.parametrize('text, needle, message', [
    ('', None, 'Write a statement'),
    ('  ;  ', None, 'Write a statement'),
    ('SELECT * FROM events LIMIT 2;\nDESCRIBE events', 'DESCRIBE events', 'One statement at a time'),
    ('USE hub', 'USE hub', 'USE is not run here'),
    ('SHOW DATABASES', 'SHOW DATABASES', 'SHOW DATABASES is not run here'),
    ('WHOAMI', 'WHOAMI', 'WHOAMI is not run here'),
    ("SELECT * FROM events WHERE id > 1 FORMAT csv", 'csv', 'FORMAT csv is MISP\'s own format'),
    ("SELECT * FROM events WHERE id > 1 LIMIT 501", '501', 'At most 500 rows per server'),
    ("SELECT * FROM evnts LIMIT 1", 'evnts', 'unknown table evnts'),
    ("SELECT COUNT(*) FROM events", 'COUNT(*)', 'COUNT(*) needs a WHERE'),
])
def test_mistakes_are_placed_on_the_text(app, caps, text, needle, message):
    from application.models import fleetQueries
    caps['query_max_limit'] = 500
    with pytest.raises(fleetQueries.StatementError) as raised:
        fleetQueries.prepare(text)
    [error] = raised.value.errors
    assert error['message'].startswith(message)
    if needle is not None:
        assert (error['start'], error['end']) == located(text, needle)


def test_a_mistake_says_its_line_and_column(app):
    from application.models import fleetQueries
    text = "SELECT *\nFROM events\nWHERE nope ~ 1 LIMIT 1"
    with pytest.raises(fleetQueries.StatementError) as raised:
        fleetQueries.prepare(text)
    [error] = raised.value.errors
    assert (error['line'], error['column']) == (3, text.index('~') - text.index('WHERE') + 1)


def test_a_statement_too_long_is_refused(app):
    from application.models import fleetQueries
    with pytest.raises(fleetQueries.StatementError, match='at most'):
        fleetQueries.prepare('SELECT * FROM events LIMIT 1 ' + ' ' * fleetQueries.MAX_STATEMENT_LENGTH)


def test_check_says_what_a_statement_is(app):
    from application.models import fleetQueries
    found = fleetQueries.describeStatement('SELECT id, info FROM events WHERE id > 0')
    assert found['ok'] and found['kind'] == 'select' and found['limit_added'] and found['columns'] == ['id', 'info']
    assert fleetQueries.describeStatement('SELECT')['ok'] is False


# The gate: nothing is searched on a server that has not just shown it runs complex queries

STATEMENTS = [
    "SELECT * FROM attributes WHERE value = '198.51.100.23' LIMIT 100",
    'SELECT COUNT(*) FROM events WHERE id = -1',
    'SELECT * FROM events LIMIT 10',  # no WHERE: still only sent to a server that runs complex queries
]


@pytest.mark.parametrize('check, role, state, status', [
    (supportAnswer('not_supported'), None, 'not_supported', 'skipped'),
    (supportAnswer('no_permission'), ROLE_WITHOUT, 'no_permission', 'error'),
    (supportAnswer('no_permission'), None, 'unavailable', 'error'),
    ((500, '<pre class="cake-error">Warning</pre>'), None, 'unknown', 'error'),
    ((200, '{"tables": {}}'), None, 'unknown', 'error'),
    ({'error': 'Server unreachable'}, None, 'unreachable', 'error'),
    ({'error': 'Request timed out'}, None, 'timeout', 'error'),
])
@pytest.mark.parametrize('statement', STATEMENTS)
def test_no_search_reaches_a_server_without_complex_queries(db, fleet, misp, check, role, state, status, statement):
    from application import redisModel
    user, _, servers = fleet
    server = servers[0]
    misp['answers'][(server.url, 'GET', '/attributes/queryDescribe')] = check
    if role is not None:
        redisModel.saveServerInfo(server.uuid, {'timestamp': 1, 'query_result': {'serverUser': {'Role': role}}})
    # What such a server would answer if asked: every row, every event counted
    misp['answers'][(server.url, 'POST', '/attributes/restSearch')] = recorded('rows_attributes')
    misp['answers'][(server.url, 'POST', '/events/restSearch')] = recorded('rows_events')
    job = runQuery(user, [server], statement)
    result = summaryOf(job, server)
    assert searches(misp) == []
    assert misp['requests'] == [(server.url, 'GET', '/attributes/queryDescribe', None)]
    assert (result.status, result.response['outcome']) == (status, state)
    assert job.status == ('done' if status == 'skipped' else 'failed')


def test_a_fresh_refusal_wins_over_a_cached_capability_and_the_role(db, fleet, misp):
    from application import redisModel
    from application.models import queryCapability
    user, _, servers = fleet
    server = servers[0]
    queryCapability.remember(server, queryCapability.capability('supported', 200, ''))
    redisModel.saveServerInfo(server.uuid, {'timestamp': 1, 'query_result': {'serverUser': {
        'Role': {**ROLE_WITH, 'perm_site_admin': True}}}})
    misp['answers'][(server.url, 'GET', '/attributes/queryDescribe')] = supportAnswer('not_supported')
    job = runQuery(user, [server], STATEMENTS[0])
    assert searches(misp) == [] and summaryOf(job, server).response['outcome'] == 'not_supported'
    assert queryCapability.get(server)['state'] == 'not_supported'  # what the run learnt, for the UI


def test_each_run_asks_again_before_searching(db, fleet, misp):
    """A server's answer is not remembered from one run to the next: one that lost the feature is not searched"""
    user, _, servers = fleet
    misp['answers'][(None, 'POST', '/events/restSearch')] = recorded('count_events')
    job = runQuery(user, servers[:2], 'SELECT COUNT(*) FROM events WHERE id > 0')
    assert [r.status for r in job.results] == ['ok', 'ok']
    misp['requests'].clear()
    misp['answers'][(servers[1].url, 'GET', '/attributes/queryDescribe')] = supportAnswer('not_supported')
    again = runQuery(user, servers[:2], 'SELECT COUNT(*) FROM events WHERE id > 0')
    assert [r.status for r in again.results] == ['ok', 'skipped']
    assert searches(misp, servers[1].url) == []
    assert len(searches(misp, servers[0].url)) == 1


def test_a_retry_through_the_jobs_api_goes_through_the_same_unit(db, fleet, misp, monkeypatch):
    import application.models.jobRunner as jobRunner
    import application.models.userJobs as userJobs
    from application.workers import tasks
    user, _, servers = fleet
    monkeypatch.setattr(tasks, 'runJob', lambda job_id: jobRunner.run(job_id))
    misp['answers'][(None, 'GET', '/attributes/queryDescribe')] = supportAnswer('not_supported')
    job = runQuery(user, servers, STATEMENTS[0])
    retry = userJobs.retry(user, job.id, only_failed=False)
    assert retry.kind == 'mispql_query' and {r.status for r in retry.results} == {'skipped'}
    assert searches(misp) == []


# Answers

def test_rows_are_flattened_kept_in_redis_and_summarised(db, fleet, misp):
    from application.models import fleetQueries
    user, _, servers = fleet
    server = servers[0]
    misp['answers'][(None, 'POST', '/events/restSearch')] = recorded('rows_events')
    job = runQuery(user, [server], 'SELECT * FROM events WHERE id > 0 LIMIT 1')
    result = summaryOf(job, server)
    summary = result.response
    assert (result.status, result.summary) == ('ok', '1 row, more on this server')
    assert (summary['outcome'], summary['rows'], summary['more'], summary['total'], summary['requests']) == \
        ('rows', 1, True, 1, 2)
    assert {'id', 'info', 'Orgc.name', 'Org.name'} <= set(summary['columns'])
    assert 'RelatedEvent' not in summary['columns']  # lists of records are dropped
    stored = fleetQueries.loadRows(job.id, server.id)
    assert stored['rows'][0]['Orgc.name'] == 'ORGNAME' and stored['rows'][0]['info'] == 'smoke'
    [search] = searches(misp)
    assert search[3]['metadata'] == 1 and search[3]['limit'] == 1  # events without their attributes
    assert 0 < fleetQueries.redisModel.redisClient.ttl(fleetQueries.rowsKey(job.id, server.id)) <= 3600


def test_rows_keep_only_the_asked_columns(db, fleet, misp):
    from application.models import fleetQueries
    user, _, servers = fleet
    misp['answers'][(None, 'POST', '/attributes/restSearch')] = recorded('rows_attributes')
    job = runQuery(user, servers[:1], 'SELECT value, ORG, eventinfo FROM attributes WHERE id > 0 ORDER BY id DESC')
    summary = summaryOf(job, servers[0]).response
    assert summary['columns'] == ['value', 'Event.Orgc.name', 'Event.info']
    assert summary['limit_added'] and summary['limit'] == 1000 and summary['total'] is None
    stored = fleetQueries.loadRows(job.id, servers[0].id)
    assert stored['rows'] == [{'value': '198.51.100.7', 'Event.Orgc.name': 'ORGNAME', 'Event.info': 'smoke'}]
    assert stored['sort'] == [['1']]  # the ORDER BY's values, kept beside the rows


@pytest.mark.parametrize('statement, answer, count', [
    ('SELECT COUNT(*) FROM events WHERE id > 0', 'count_events', 1),
    ('SELECT COUNT(*) FROM attributes WHERE id > 0', 'count_attributes', 1),
])
def test_counts(db, fleet, misp, statement, answer, count):
    user, _, servers = fleet
    table = statement.split()[3]
    misp['answers'][(None, 'POST', f'/{table}/restSearch')] = recorded(answer)
    job = runQuery(user, servers, statement)
    assert [(r.response['outcome'], r.response['count'], r.summary) for r in job.results] == \
        [('count', count, f'Count: {count}')] * 3
    assert job.status == 'done'


def test_describe_is_kept_in_the_summary_and_the_cache(db, fleet, misp):
    from application.models import queryCapability
    user, _, servers = fleet
    misp['answers'][(None, 'GET', '/events/queryDescribe')] = recorded('describe_events')
    job = runQuery(user, servers[:1], 'DESCRIBE events')
    summary = summaryOf(job, servers[0]).response
    assert summary['outcome'] == 'describe' and summary['requests'] == 1  # a DESCRIBE is its own check
    assert len(summary['describe']['fields']) == 24 and summary['describe']['limits']['max_depth'] == 5
    misp['requests'].clear()
    assert queryCapability.describe(servers[0], 'events')['cached'] is True
    assert misp['requests'] == []


def test_show_tables_lists_the_tables_answering(db, fleet, misp):
    user, _, servers = fleet
    misp['answers'][(None, 'GET', '/events/queryDescribe')] = recorded('describe_events')
    job = runQuery(user, servers[:1], 'SHOW TABLES')
    summary = summaryOf(job, servers[0]).response
    assert summary['outcome'] == 'tables' and summary['tables'] == ['attributes', 'events']
    assert summary['requests'] == 11


def test_misp_query_errors_are_placed_on_the_text(db, fleet, misp):
    user, _, servers = fleet
    statement = ANSWERS['error_several']['about']
    misp['answers'][(None, 'POST', '/attributes/restSearch')] = recorded('error_several')
    job = runQuery(user, servers[:1], statement)
    result = summaryOf(job, servers[0])
    errors = result.response['errors']
    assert result.response['outcome'] == 'query_errors' and result.status == 'error'
    assert result.summary == '4 errors in the query: unknown field'
    assert [e['code'] for e in errors] == ['unknown_field', 'bad_type', 'bad_type', 'bad_type']
    assert (errors[0]['start'], errors[0]['end']) == located(statement, 'bogus')
    assert statement[errors[1]['start']:errors[1]['end']] == "id = 'x'"
    assert statement[errors[2]['start']:errors[2]['end']] == "type LIKE 'a%b'"


@pytest.mark.parametrize('answer, outcome, status', [
    (recorded('search_no_permission'), 'no_permission', 'error'),
    (recorded('search_not_implemented'), 'not_supported', 'skipped'),
    ((500, '{"name": "An Internal Error Has Occurred."}'), 'refused', 'error'),
    ((200, '<html>Login</html>'), 'bad_answer', 'error'),
    ((200, '{"response": [1, 2]}'), 'bad_answer', 'error'),
    ({'error': 'The answer is larger than 1 MB', 'too_large': True}, 'too_large', 'error'),
    ({'error': 'Request timed out'}, 'timeout', 'error'),
    ({'error': 'SSL Error'}, 'unreachable', 'error'),
])
def test_other_answers_to_a_search(db, fleet, misp, answer, outcome, status):
    user, _, servers = fleet
    misp['answers'][(None, 'POST', '/tags/restSearch')] = answer
    job = runQuery(user, servers[:1], "SELECT * FROM tags WHERE name LIKE 'tlp:%' LIMIT 5")
    result = summaryOf(job, servers[0])
    assert (result.response['outcome'], result.status) == (outcome, status)
    assert result.summary
    # The search's own status, never the support check's
    assert result.http_status == (None if isinstance(answer, dict) else answer[0])


def test_a_statement_that_no_longer_passes_sends_nothing(db, fleet, misp, caps):
    user, _, servers = fleet
    caps['query_max_limit'] = 10
    job = runQuery(user, servers[:1], 'SELECT * FROM events WHERE id > 0 LIMIT 50')
    result = summaryOf(job, servers[0])
    assert result.response['outcome'] == 'invalid' and result.summary.startswith('At most 10 rows')
    assert misp['requests'] == []


# Merging

def test_merged_rows_are_sorted_again_numbers_as_numbers_empties_last(app):
    from application.models import fleetQueries
    statement = 'SELECT value FROM attributes WHERE id > 0 ORDER BY timestamp DESC LIMIT 10'
    jobId = f'merge-{uuid.uuid4().hex}'
    fleetQueries.storeRows(jobId, 1, ['value'], [{'value': 'a'}, {'value': 'b'}, {'value': 'c'}],
                           [['9'], ['100'], [None]], 60)
    fleetQueries.storeRows(jobId, 2, ['value'], [{'value': 'd'}], [['50']], 60)
    merged = fleetQueries.merge(statement, [{'id': 1, 'name': 'one'}, {'id': 2, 'name': 'two'},
                                            {'id': 3, 'name': 'gone'}], jobId)
    assert [(r['value'], r['_server_name']) for r in merged['rows']] == \
        [('b', 'one'), ('d', 'two'), ('a', 'one'), ('c', 'one')]
    assert merged['columns'] == ['value'] and merged['expired_servers'] == [3]
    unsorted = fleetQueries.merge('SELECT value FROM attributes WHERE id > 0 LIMIT 10',
                                  [{'id': 2, 'name': 'two'}, {'id': 1, 'name': 'one'}], jobId)
    assert [r['value'] for r in unsorted['rows']] == ['d', 'a', 'b', 'c']  # by server, in the job's order


def test_ascending_sort_keeps_empties_last_and_ties_by_server(app):
    from application.models import fleetQueries
    jobId = f'merge-{uuid.uuid4().hex}'
    fleetQueries.storeRows(jobId, 1, ['v'], [{'v': 1}, {'v': 2}], [[None], ['x']], 60)
    fleetQueries.storeRows(jobId, 2, ['v'], [{'v': 3}, {'v': 4}], [['x'], ['-1.5']], 60)
    merged = fleetQueries.merge('SELECT * FROM attributes WHERE id > 0 ORDER BY value LIMIT 5',
                                [{'id': 1, 'name': 'a'}, {'id': 2, 'name': 'b'}], jobId)
    assert [r['v'] for r in merged['rows']] == [4, 2, 3, 1]


# API

@pytest.fixture()
def queued(monkeypatch):
    from application.workers import tasks
    calls = []
    monkeypatch.setattr(tasks, 'runJob', lambda job_id: calls.append(job_id))
    return calls


def test_check_endpoint(client, auth_headers, fleet):
    user, _, _ = fleet
    response = client.post('/queries/check', json={'statement': 'SELECT * FROM events WHERE id > 0'},
                           headers=auth_headers(user))
    body = response.get_json()
    assert response.status_code == 200 and body['ok'] and body['limit_added']
    body = client.post('/queries/check', json={'statement': 'SELECT * FROM'}, headers=auth_headers(user)).get_json()
    assert body['ok'] is False and body['errors'][0]['start'] == len('SELECT * FROM')


def test_a_statement_with_mistakes_creates_no_job(db, client, auth_headers, fleet, queued):
    from application.DBModels import Job
    user, _, servers = fleet
    before = Job.query.count()
    response = client.post('/queries', json={'statement': 'USE hub', 'server_ids': [servers[0].id]},
                           headers=auth_headers(user))
    assert response.status_code == 400
    assert response.get_json()['errors'][0]['message'].startswith('USE is not run here')
    assert Job.query.count() == before and queued == []


def test_a_fleet_is_queried_on_its_servers_by_name(db, client, auth_headers, fleet, queued):
    user, theFleet, servers = fleet
    response = client.post('/queries', json={'statement': 'SELECT * FROM events WHERE id > 0', 'fleet_id': theFleet.id},
                           headers=auth_headers(user))
    assert response.status_code == 202, response.get_json()
    body = response.get_json()
    assert queued == [body['job_id']]
    assert [r['server_name'] for r in body['job']['results']] == ['misp-a', 'misp-b', 'misp-c']
    assert body['job']['kind'] == 'mispql_query' and body['job']['params'] == {
        'statement': 'SELECT * FROM events WHERE id > 0'}
    assert body['job']['title'] == 'SELECT * FROM events WHERE id > 0 on 3 servers'
    assert body['notes'] == ['No LIMIT: each server returns at most 1000 rows']


@pytest.mark.parametrize('payload, status', [
    ({'server_ids': [999999]}, 404),
    ({}, 400),
    ({'server_ids': 'all'}, 400),
    ({'fleet_id': 999999}, 404),
])
def test_only_ones_own_servers_are_queried(db, client, auth_headers, fleet, make_user, queued, payload, status):
    user, theFleet, servers = fleet
    response = client.post('/queries', json={'statement': 'SHOW TABLES', **payload}, headers=auth_headers(user))
    assert response.status_code == status and queued == []
    stranger = make_user(f'stranger-{uuid.uuid4().hex[:6]}@test.local')
    for body in ({'server_ids': [servers[0].id]}, {'fleet_id': theFleet.id}):
        response = client.post('/queries', json={'statement': 'SHOW TABLES', **body}, headers=auth_headers(stranger))
        assert response.status_code == 404 and queued == []


def test_query_runs_are_not_started_through_the_jobs_api(db, client, auth_headers, fleet, queued):
    user, _, servers = fleet
    response = client.post('/jobs', json={'kind': 'mispql_query', 'server_ids': [servers[0].id],
                                          'params': {'statement': 'SHOW TABLES'}}, headers=auth_headers(user))
    assert response.status_code == 400 and queued == []


def test_a_run_and_its_rows_are_its_owners(db, client, auth_headers, fleet, misp, make_user):
    import application.models.jobs as jobModel
    user, _, servers = fleet
    misp['answers'][(servers[1].url, 'GET', '/attributes/queryDescribe')] = supportAnswer('not_supported')
    misp['answers'][(None, 'POST', '/attributes/restSearch')] = recorded('rows_attributes')
    job = runQuery(user, servers[:2], 'SELECT value FROM attributes WHERE id > 0 LIMIT 5')
    headers = auth_headers(user)

    run = client.get(f'/queries/{job.id}', headers=headers).get_json()
    assert run['statement'] == 'SELECT value FROM attributes WHERE id > 0 LIMIT 5' and run['rows_readable']
    assert [(r['status'], r['rows_kept'], r['response']['outcome']) for r in run['results']] == \
        [('ok', True, 'rows'), ('skipped', None, 'not_supported')]
    page = client.get(f'/queries/{job.id}/rows?limit=10', headers=headers).get_json()
    assert page['total'] == 1 and page['columns'] == ['value'] and page['expired_servers'] == []
    assert page['rows'] == [{'_server_id': servers[0].id, '_server_name': servers[0].name, 'value': '198.51.100.7'}]
    assert client.get(f'/queries/{job.id}/rows?server_id=999999', headers=headers).status_code == 404
    assert client.get(f'/queries/{job.id}/rows?limit=1001', headers=headers).status_code == 400

    admin = make_user(f'admin-q-{uuid.uuid4().hex[:6]}@test.local', is_admin=True)
    adminRun = client.get(f'/queries/{job.id}', headers=auth_headers(admin)).get_json()
    assert adminRun['rows_readable'] is False and adminRun['results'][0]['rows_kept'] is None
    assert client.get(f'/queries/{job.id}/rows', headers=auth_headers(admin)).status_code == 403
    stranger = make_user(f'stranger-q-{uuid.uuid4().hex[:6]}@test.local')
    assert client.get(f'/queries/{job.id}', headers=auth_headers(stranger)).status_code == 404
    assert client.get(f'/queries/{job.id}/rows', headers=auth_headers(stranger)).status_code == 404

    other = jobModel.create(user, 'rest_query', servers[:1], params={'method': 'GET', 'url': '/servers/getVersion'})
    assert client.get(f'/queries/{other.id}', headers=headers).status_code == 404


def test_rows_say_when_they_have_expired(db, client, auth_headers, fleet, misp):
    from application.models import fleetQueries
    user, _, servers = fleet
    misp['answers'][(None, 'POST', '/attributes/restSearch')] = recorded('rows_attributes')
    job = runQuery(user, servers[:1], 'SELECT value FROM attributes WHERE id > 0 LIMIT 5')
    fleetQueries.redisModel.redisClient.delete(fleetQueries.rowsKey(job.id, servers[0].id))
    headers = auth_headers(user)
    assert client.get(f'/queries/{job.id}', headers=headers).get_json()['results'][0]['rows_kept'] is False
    page = client.get(f'/queries/{job.id}/rows', headers=headers).get_json()
    assert page['rows'] == [] and page['expired_servers'] == [servers[0].id]


def test_capabilities_and_fields_for_the_editor(db, client, auth_headers, fleet, misp):
    user, theFleet, servers = fleet
    misp['answers'][(servers[2].url, 'GET', '/attributes/queryDescribe')] = supportAnswer('not_supported')
    headers = auth_headers(user)
    found = client.get(f'/queries/capabilities?fleet_id={theFleet.id}', headers=headers).get_json()['servers']
    assert [(s['server_name'], s['state']) for s in found] == \
        [('misp-a', 'supported'), ('misp-b', 'supported'), ('misp-c', 'not_supported')]

    misp['answers'][(None, 'GET', '/events/queryDescribe')] = recorded('describe_events')
    ids = f'{servers[0].id},{servers[2].id}'
    found = client.get(f'/queries/describe?table=events&server_ids={ids}', headers=headers).get_json()['servers']
    assert [(s['server_id'], s['state']) for s in found] == [(servers[0].id, 'supported'), (servers[2].id, 'supported')]
    assert 'eventinfo' in found[0]['fields']
    asked = len(misp['requests'])
    again = client.get(f'/queries/describe?table=events&server_ids={ids}', headers=headers).get_json()['servers']
    assert all(s['cached'] for s in again) and len(misp['requests']) == asked
    assert client.get(f'/queries/describe?table=nope&server_ids={ids}', headers=headers).status_code == 400
    assert client.get('/queries/describe?table=events&server_ids=x', headers=headers).status_code == 400


def test_forgetting_a_server_forgets_its_fields(db, fleet, misp):
    from application import redisModel
    from application.models import queryCapability
    _, _, servers = fleet
    misp['answers'][(None, 'GET', '/events/queryDescribe')] = recorded('describe_events')
    queryCapability.describe(servers[0], 'events')
    key = queryCapability.describeKey(servers[0].id, 'events')
    assert redisModel.redisClient.exists(key)
    queryCapability.forget(servers[0].id)
    assert not redisModel.redisClient.exists(key)


# Reading an answer up to a size

class StreamedResponse:
    def __init__(self, chunks, headers=None):
        self.chunks = chunks
        self.headers = headers or {}
        self.status_code = 200
        self.closed = False
        self._content = False

    def iter_content(self, chunk_size=1):
        yield from self.chunks

    def close(self):
        self.closed = True

    @property
    def content(self):
        return self._content


@pytest.mark.parametrize('chunks, headers, kept', [
    ([b'a' * 10, b'b' * 10], {}, True),
    ([b'a' * 10, b'b' * 11], {}, False),
    ([b'a'], {'Content-Length': '21'}, False),
    ([b'a' * 20], {'Content-Length': '21', 'Content-Encoding': 'gzip'}, True),
])
def test_an_answer_is_read_up_to_a_size(app, monkeypatch, chunks, headers, kept):
    from application.controllers import utils
    response = StreamedResponse(chunks, headers)
    sent = []

    class Session:
        def request(self, method, url, **options):
            sent.append(options)
            return response

    class Server:
        url = 'https://hub.test/'
        authkey = 'k' * 40
        skip_ssl = False

    monkeypatch.setattr(utils, 'getRequestPSession', lambda: Session())
    answer = utils.mispRawRequest(Server(), 'POST', '/events/restSearch', data={'limit': 1}, max_bytes=20)
    assert sent[0]['stream'] is True
    if kept:
        assert answer is response and answer.content == b''.join(chunks)
    else:
        assert answer == {'error': 'The answer is larger than 20 bytes', 'too_large': True} and response.closed


def test_a_read_timeout_in_the_body_is_a_timeout(app, monkeypatch):
    from application.controllers import utils

    class Slow(StreamedResponse):
        def iter_content(self, chunk_size=1):
            raise requests.exceptions.ConnectionError('HTTPSConnectionPool(host=hub.test): Read timed out.')
            yield b''

    class Session:
        def request(self, method, url, **options):
            return Slow([])

    class Server:
        url = 'https://hub.test/'
        authkey = 'k'
        skip_ssl = False

    monkeypatch.setattr(utils, 'getRequestPSession', lambda: Session())
    assert utils.mispRawRequest(Server(), 'GET', '/x', max_bytes=10) == {'error': 'Request timed out'}
