"""The history of saved queries: every number a server answered to a saved query, one row a day kept up to date,
retention, the API that draws the charts, and the Prometheus series of scheduled saved queries."""
import re
import time

import pytest

from test_fleet_queries import FakeResponse, caps, fleet, misp, recorded, supportAnswer  # noqa: F401
from test_prometheus import parse
from test_saved_queries import (COUNT, SELECT, countAnswer, kept, published, runSaved, runs, save,  # noqa: F401
                                watched)

HOUR, DAY = 3600, 86400
BASE = 1_790_000_000 - 1_790_000_000 % DAY


@pytest.fixture()
def keep(monkeypatch):
    """The history settings as saved in config.json; the others keep their value"""
    import application.models.setting as settingModel
    values = {'query_history_raw_days': 30, 'query_history_day_days': 0}
    original = settingModel.getRefreshValue
    monkeypatch.setattr(settingModel, 'getRefreshValue',
                        lambda name: values[name] if name in values else original(name))
    return values


def rowsOf(saved, tier):
    from application.DBModels import SavedQuerySample
    return SavedQuerySample.query.filter_by(saved_query_id=saved.id, tier=tier) \
        .order_by(SavedQuerySample.server_id, SavedQuerySample.ts).all()


def record(saved, server, ts, value, more=False):
    from application import db
    from application.models import savedQueryHistory
    savedQueryHistory.record(saved.id, server.id, ts, value, more)
    db.session.commit()


# Writing

def test_each_number_a_run_keeps_is_kept_over_time(db, fleet, misp, runs, published):
    user, fleetRow, servers = fleet
    misp['answers'][(None, 'POST', '/attributes/restSearch')] = countAnswer(3)
    misp['answers'][(servers[1].url, 'POST', '/attributes/restSearch')] = countAnswer(0)
    misp['answers'][(servers[2].url, 'GET', '/attributes/queryDescribe')] = supportAnswer('not_supported')
    saved = watched(user, fleetRow)
    runSaved(saved)
    results = kept(saved)
    expected = {servers[0].id: 3, servers[1].id: 0}
    assert {(r.server_id, r.ts, r.value, r.more) for r in rowsOf(saved, 'raw')} == \
        {(serverId, results[serverId].checked_at, value, False) for serverId, value in expected.items()}
    # A server that could not answer a number leaves a gap
    assert servers[2].id not in {r.server_id for r in rowsOf(saved, 'raw')}
    assert {(r.server_id, r.ts, r.value, r.low, r.high, r.samples) for r in rowsOf(saved, 'day')} == \
        {(serverId, results[serverId].checked_at - results[serverId].checked_at % DAY, value, value, value, 1)
         for serverId, value in expected.items()}


def test_a_day_keeps_its_last_lowest_and_highest_answer(db, fleet):
    user, fleetRow, servers = fleet
    saved = watched(user, fleetRow)
    for offset, value in ((HOUR, 5), (2 * HOUR, 9), (3 * HOUR, 2), (4 * HOUR, 4)):
        record(saved, servers[0], BASE + offset, value)
    record(saved, servers[0], BASE + 4 * HOUR, 4)  # The same answer recorded again changes nothing
    record(saved, servers[0], BASE + DAY + HOUR, 7, more=True)
    assert [(r.ts, r.value, r.low, r.high, r.samples, r.more) for r in rowsOf(saved, 'day')] == [
        (BASE, 4, 2, 9, 4, False), (BASE + DAY, 7, 7, 7, 1, True)]
    assert len(rowsOf(saved, 'raw')) == 5


def test_a_select_that_found_more_rows_than_its_limit_says_so(db, fleet, misp, runs, published):
    user, fleetRow, servers = fleet
    misp['answers'][(None, 'POST', '/attributes/restSearch')] = recorded('rows_attributes')
    saved = save(user, statement=SELECT.replace('LIMIT 100', 'LIMIT 1'), server_ids=[servers[0].id],
                 schedule_minutes=60, expectation={'comparator': 'eq', 'value': 0})
    runSaved(saved)
    [raw], [day] = rowsOf(saved, 'raw'), rowsOf(saved, 'day')
    assert (raw.value, raw.more, day.more) == (1, True, True)


def test_a_new_statement_starts_the_history_again(db, fleet):
    from application.models import savedQueries
    user, fleetRow, servers = fleet
    saved, other = watched(user, fleetRow), watched(user, fleetRow)
    for row in (saved, other):
        for server in servers[:2]:
            record(row, server, BASE + HOUR, 1)
    # A new expectation or target keeps it: it still answers the same question
    savedQueries.update(user, saved.id, {'expectation': {'comparator': 'lte', 'value': 5}})
    savedQueries.update(user, saved.id, {'server_ids': [servers[0].id]})
    assert len(rowsOf(saved, 'raw')) == 2 and len(rowsOf(saved, 'day')) == 2
    savedQueries.update(user, saved.id, {'statement': COUNT.replace('23', '24')})
    assert rowsOf(saved, 'raw') == [] and rowsOf(saved, 'day') == []
    assert len(rowsOf(other, 'raw')) == 2


def test_the_history_goes_with_its_saved_query_its_server_and_its_owner(db, fleet, make_user):
    from application.DBModels import Fleet, SavedQuerySample, Server
    from application.models import savedQueries, users
    user, fleetRow, servers = fleet
    saved, other = watched(user, fleetRow), watched(user, fleetRow)
    for row in (saved, other):
        for server in servers[:2]:
            record(row, server, BASE + HOUR, 1)
    db.session.delete(db.session.get(Server, servers[0].id))
    db.session.commit()
    assert {r.server_id for r in rowsOf(other, 'raw') + rowsOf(other, 'day')} == {servers[1].id}
    savedId = saved.id
    savedQueries.delete(user, savedId)
    assert SavedQuerySample.query.filter_by(saved_query_id=savedId).count() == 0
    assert len(rowsOf(other, 'raw')) == 1

    owner = make_user(f'history-{time.time_ns()}@test.local')
    own = Fleet(name='Own', description='', user_id=owner.id, timestamp=1)
    db.session.add(own)
    db.session.commit()
    owned = save(owner, fleet_id=own.id)
    ownedId = owned.id
    record(owned, servers[1], BASE + HOUR, 1)  # Its owner's servers are not needed to keep rows
    users.delete(owner.id)
    assert SavedQuerySample.query.filter_by(saved_query_id=ownedId).count() == 0


# Retention

def test_rows_older_than_their_tier_retention_are_trimmed(db, fleet, keep):
    from application.models import savedQueryHistory
    user, fleetRow, servers = fleet
    saved = watched(user, fleetRow)
    now = BASE + 1000 * DAY + 37 * 60
    keep.update({'query_history_raw_days': 7, 'query_history_day_days': 0})
    for age in (6, 8, 500):
        record(saved, servers[0], now - age * DAY, age)
    report = savedQueryHistory.trim(now)
    assert [r.value for r in rowsOf(saved, 'raw')] == [6]
    assert sorted(r.value for r in rowsOf(saved, 'day')) == [6, 8, 500]  # Kept as long as the saved query
    assert set(report) == {'raw'}
    keep['query_history_day_days'] = 365
    assert savedQueryHistory.trim(now)['day'] >= 1  # Earlier tests' rows too: the database lives for the session
    assert sorted(r.value for r in rowsOf(saved, 'day')) == [6, 8]


def test_history_defaults():
    import application.models.setting as settingModel
    from application.models import savedQueryHistory
    assert (settingModel.getValue('query_history_raw_days'), settingModel.getValue('query_history_day_days')) == \
        (30, 0)
    assert savedQueryHistory.retention() == {'raw': 30 * DAY, 'day': None}


@pytest.mark.parametrize('raw, day, expected', [
    (3, 0, (7, None)),  # Under the minimum
    (60, 100, (60, 365)),  # Days drawn for a year at least
    (500, 400, (500, 500)),  # Days never kept for less than every answer
    ('abc', None, (30, None)),  # Not a number: the default
])
def test_history_values_edited_by_hand_are_brought_back_in_bounds(keep, raw, day, expected):
    from application.models import savedQueryHistory
    keep.update({'query_history_raw_days': raw, 'query_history_day_days': day})
    retention = savedQueryHistory.retention()
    assert (retention['raw'] // DAY, None if retention['day'] is None else retention['day'] // DAY) == expected


@pytest.mark.parametrize('name, value, message', [
    ('query_history_raw_days', 6, 'at least 7'),
    ('query_history_raw_days', 366, 'at most 365'),
    ('query_history_day_days', 100, 'at least 365'),
    ('query_history_day_days', 3651, 'at most 3650'),
])
def test_history_values_are_validated(keep, name, value, message):
    import application.models.setting as settingModel
    with pytest.raises(settingModel.SettingError, match=re.escape(message)):
        settingModel.validate(name, value)


@pytest.mark.parametrize('name, value', [
    ('query_history_raw_days', 365), ('query_history_day_days', 0), ('query_history_day_days', 365),
])
def test_history_values_accepted(keep, name, value):
    import application.models.setting as settingModel
    assert settingModel.validate(name, value) == value


# Reading

def test_the_history_draws_each_current_server_per_range(db, client, auth_headers, fleet, keep, monkeypatch):
    from types import SimpleNamespace
    from application.models import savedQueryHistory
    user, fleetRow, servers = fleet
    byName = {server.name: server for server in servers}
    saved = save(user, fleet_id=fleetRow.id, schedule_minutes=15, expectation={'comparator': 'lte', 'value': 5})
    now = BASE + 1000 * DAY + 12 * HOUR + 600
    monkeypatch.setattr(savedQueryHistory, 'time', SimpleNamespace(time=lambda: now))
    hourAgo = now - now % HOUR - 20 * DAY  # Two answers in one hour, 20 days ago
    for name, shift in (('misp-a', 0), ('misp-b', 10)):
        server = byName[name]
        record(saved, server, now - 60 * DAY, 1 + shift)
        record(saved, server, hourAgo + 60, 4 + shift)
        record(saved, server, hourAgo + 120, 2 + shift)
        record(saved, server, now - 2 * HOUR, 3 + shift)
        record(saved, server, now - HOUR, 6 + shift)

    def history(range=None, headers=None):
        query = f'?range={range}' if range else ''
        return client.get(f'/queries/saved/{saved.id}/history{query}', headers=headers or auth_headers(user))

    week = history().json
    assert (week['range'], week['tier'], week['interval_s'], week['partial_since']) == ('7d', 'raw', 900, None)
    assert (week['kind'], week['expectation'], week['expectation_text'], week['limit']) == \
        ('count', {'comparator': 'lte', 'value': 5}, 'at most 5', None)
    assert [entry['server_name'] for entry in week['servers']] == ['misp-a', 'misp-b', 'misp-c']
    a = week['servers'][0]
    assert (a['points'], a['lows'], a['highs'], a['capped']) == ([[now - 2 * HOUR, 3], [now - HOUR, 6]], [], [], [])
    assert week['servers'][2]['points'] == []

    month = history('30d').json
    assert (month['tier'], month['interval_s']) == ('hour', HOUR)
    b = month['servers'][1]
    assert b['points'][0] == [hourAgo, 12] and b['lows'][0] == [hourAgo, 12] and b['highs'][0] == [hourAgo, 14]
    assert len(b['points']) == 3

    quarter = history('90d').json
    assert (quarter['tier'], quarter['interval_s'], quarter['partial_since']) == ('day', DAY, now - now % DAY)
    a = quarter['servers'][0]
    assert a['points'][0] == [(now - 60 * DAY) - (now - 60 * DAY) % DAY, 1]
    assert a['points'][-1] == [now - now % DAY, 6]
    assert (a['lows'][-1], a['highs'][-1]) == ([now - now % DAY, 3], [now - now % DAY, 6])
    assert quarter['retention'] == {'raw_days': 30, 'day_days': None}

    # While every answer is kept for less than 30 days, the month is drawn per day
    keep['query_history_raw_days'] = 14
    assert history('30d').json['tier'] == 'day'


def test_servers_out_of_the_target_are_not_drawn_but_come_back(db, client, auth_headers, fleet):
    from application.models import savedQueries
    user, fleetRow, servers = fleet
    saved = save(user, server_ids=[s.id for s in servers], schedule_minutes=60)
    now = int(time.time())
    for server in servers:
        record(saved, server, now - HOUR, 1)
    savedQueries.update(user, saved.id, {'server_ids': [servers[0].id]})
    drawn = client.get(f'/queries/saved/{saved.id}/history', headers=auth_headers(user)).json['servers']
    assert [(entry['server_id'], entry['points']) for entry in drawn] == [(servers[0].id, [[now - HOUR, 1]])]
    savedQueries.update(user, saved.id, {'server_ids': [servers[1].id, servers[0].id]})
    drawn = client.get(f'/queries/saved/{saved.id}/history', headers=auth_headers(user)).json['servers']
    assert [(entry['server_id'], len(entry['points'])) for entry in drawn] == [(servers[1].id, 1), (servers[0].id, 1)]


def test_a_select_history_says_its_limit_and_where_it_was_capped(db, client, auth_headers, fleet, caps):
    user, fleetRow, servers = fleet
    limited = save(user, statement=SELECT, server_ids=[servers[0].id])
    unlimited = save(user, statement=SELECT.replace(' LIMIT 100', ''), server_ids=[servers[0].id])
    now = int(time.time())
    record(limited, servers[0], now - HOUR, 100, more=True)
    answer = client.get(f'/queries/saved/{limited.id}/history', headers=auth_headers(user)).json
    assert (answer['kind'], answer['limit'], answer['interval_s']) == ('select', 100, DAY)  # Run by hand only
    assert answer['servers'][0]['capped'] == [now - HOUR]
    caps['query_max_limit'] = 250
    assert client.get(f'/queries/saved/{unlimited.id}/history', headers=auth_headers(user)).json['limit'] == 250


@pytest.mark.parametrize('statement, query, status, field', [
    (COUNT, '?range=2w', 400, 'range'),
    ('DESCRIBE events', '', 400, None),
    ('SHOW TABLES', '', 400, None),
])
def test_what_has_no_history(db, client, auth_headers, fleet, statement, query, status, field):
    user, fleetRow, _ = fleet
    saved = save(user, statement=statement, fleet_id=fleetRow.id)
    answer = client.get(f'/queries/saved/{saved.id}/history{query}', headers=auth_headers(user))
    assert (answer.status_code, answer.json.get('field')) == (status, field), answer.json


def test_the_history_is_its_owners(db, client, auth_headers, fleet, make_user):
    user, fleetRow, _ = fleet
    saved = save(user, fleet_id=fleetRow.id)
    other = make_user(f'other-{time.time_ns()}@test.local')
    assert client.get(f'/queries/saved/{saved.id}/history', headers=auth_headers(other)).status_code == 404


# Prometheus

def scraped(client, headers):
    return parse(client.get('/metrics', headers=headers).get_data(as_text=True))


def labelsOf(saved, server, kind='count', fleetName='Query fleet'):
    return frozenset({('saved_query', saved.name), ('saved_query_id', str(saved.id)), ('kind', kind),
                      ('server', server.name), ('server_id', str(server.id)), ('fleet', fleetName)})


def test_scheduled_saved_queries_reach_prometheus(db, client, auth_headers, fleet, misp, runs, published,
                                                   make_user):
    user, fleetRow, servers = fleet
    misp['answers'][(None, 'POST', '/attributes/restSearch')] = countAnswer(3)
    misp['answers'][(servers[1].url, 'POST', '/attributes/restSearch')] = countAnswer(0)
    misp['answers'][(servers[2].url, 'GET', '/attributes/queryDescribe')] = supportAnswer('not_supported')
    scheduled = watched(user, fleetRow, name='No "bad" IP\\here')
    unexpected = save(user, fleet_id=fleetRow.id, schedule_minutes=1440)
    byHand = save(user, fleet_id=fleetRow.id, expectation={'comparator': 'eq', 'value': 0})
    for saved in (scheduled, unexpected, byHand):
        runSaved(saved)
    text = client.get('/metrics', headers=auth_headers(user)).get_data(as_text=True)
    samples = parse(text)
    results = kept(scheduled)
    a, b, c = servers
    assert samples[('mfc_saved_query_schedule_enabled', frozenset())] == 1
    assert samples[('mfc_saved_query_value', labelsOf(scheduled, a))] == 3
    assert samples[('mfc_saved_query_value', labelsOf(scheduled, b))] == 0
    assert samples[('mfc_saved_query_expectation_met', labelsOf(scheduled, a))] == 0
    assert samples[('mfc_saved_query_expectation_met', labelsOf(scheduled, b))] == 1
    assert samples[('mfc_saved_query_up', labelsOf(scheduled, a))] == 1
    assert samples[('mfc_saved_query_last_run_timestamp_seconds', labelsOf(scheduled, a))] == \
        results[a.id].checked_at
    # Could not give a number there: down, and no value
    assert samples[('mfc_saved_query_up', labelsOf(scheduled, c))] == 0
    assert ('mfc_saved_query_value', labelsOf(scheduled, c)) not in samples
    # Without an expectation: the value, nothing met or not
    assert samples[('mfc_saved_query_value', labelsOf(unexpected, a))] == 3
    assert ('mfc_saved_query_expectation_met', labelsOf(unexpected, a)) not in samples
    # A query run by hand only is not watched; statements never leave
    assert not [key for key in samples if ('saved_query_id', str(byHand.id)) in key[1]]
    assert '198.51.100.23' not in text

    other = make_user(f'prom-other-{time.time_ns()}@test.local')
    assert not [key for key in scraped(client, auth_headers(other)) if key[0] != 'mfc_saved_query_schedule_enabled'
                and key[0].startswith('mfc_saved_query')]


def test_no_saved_query_series_while_scheduled_runs_are_off(db, client, auth_headers, fleet, misp, runs, published,
                                                            monkeypatch):
    import application.models.setting as settingModel
    user, fleetRow, _ = fleet
    misp['answers'][(None, 'POST', '/attributes/restSearch')] = countAnswer(3)
    runSaved(watched(user, fleetRow))
    original = settingModel.getRefreshValue
    monkeypatch.setattr(settingModel, 'getRefreshValue',
                        lambda name: False if name == 'query_schedule_enabled' else original(name))
    samples = scraped(client, auth_headers(user))
    assert {key: value for key, value in samples.items() if key[0].startswith('mfc_saved_query')} == \
        {('mfc_saved_query_schedule_enabled', frozenset()): 0}
